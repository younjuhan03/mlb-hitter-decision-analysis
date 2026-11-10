"""Recheck the uploaded snapshot without altering forecasts or evaluation locks.

Run: python -m src.review_verification
Outputs go to supplement/. No network requests are made.
"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json
import numpy as np
import pandas as pd
from scipy.stats import hypergeom, binom
from sklearn.pipeline import make_pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from sklearn.metrics import roc_auc_score
from . import study, robustness as rob

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'supplement'

def main():
    OUT.mkdir(exist_ok=True)
    features = pd.read_csv(ROOT/'data/processed/features.csv')
    predictions = pd.read_csv(ROOT/'reports/historical_predictions.csv')
    queue = pd.read_csv(ROOT/'reports/2027_scouting_queue.csv')
    result = {'review_date': '2026-10-04', 'executed_at_utc': datetime.now(timezone.utc).isoformat(), 'network_requery': False}
    # Reconcile all cached sources against their original metadata.
    source_checks = []
    for meta in sorted((ROOT/'data/raw').glob('*.meta.json')):
        m = json.loads(meta.read_text())
        name = meta.name.replace('.meta.json', '')
        files = [f for f in (ROOT/'data/raw').glob(name+'.*') if f != meta]
        assert len(files) == 1
        digest = hashlib.sha256(files[0].read_bytes()).hexdigest()
        assert digest == m['sha256'], str(files[0])
        source_checks.append({'file': files[0].name, 'sha256': digest, 'matches': True})
    pd.DataFrame(source_checks).to_csv(OUT/'cached_source_hash_checks.csv', index=False)
    result['cached_sources_checked'] = len(source_checks)
    source = pd.read_csv(ROOT/'data/raw/custom_2026.csv')
    expected = pd.read_csv(ROOT/'data/raw/expected_2026.csv')
    official = json.loads((ROOT/'data/raw/mlb_hitting_2026.json').read_text())['stats'][0]['splits']
    mlb = pd.Series({x['player']['id']:x['stat']['plateAppearances'] for x in official})
    dif = source.set_index('player_id').pa - mlb.reindex(source.player_id)
    assert source.pa.sum() == mlb.sum() == 183849
    assert dif.notna().all() and dif.ne(0).sum() == 8 and dif.abs().max() == 1
    assert np.array_equal(source.set_index('player_id').pa.sort_index(), expected.set_index('player_id').pa.sort_index())
    assert np.allclose(source.set_index('player_id').woba.sort_index(), expected.set_index('player_id').woba.sort_index(), equal_nan=True)
    result['pa_audit'] = {'total':183849,'individual_discrepancies':8,'max_absolute_difference':1,'reason':'unresolved'}
    people = {p['id']:p for f in (ROOT/'data/raw').glob('people_*.json') if not f.name.endswith('.meta.json') for p in json.loads(f.read_text())['people']}
    evidence = []
    for row in queue.itertuples():
        for year in [2025,2026]:
            raw = pd.read_csv(ROOT/f'data/raw/custom_{year}.csv').set_index('player_id').loc[row.player_id]
            e = pd.read_csv(ROOT/f'data/raw/expected_{year}.csv').set_index('player_id').loc[row.player_id]
            age = (pd.Timestamp(year=year,month=7,day=1)-pd.Timestamp(people[row.player_id]['birthDate'])).days/365.2425
            evidence.append({'player_id':row.player_id,'name':row.display_name,'year':year,'pa':int(raw.pa),'woba':raw.woba,'xwoba':e.est_woba,'hard_hit_pct':raw.hard_hit_percent,'k_percent':raw.k_percent,'bb_percent':raw.bb_percent,'iso':raw.slg_percent-raw.batting_avg,'mean_launch_angle':raw.launch_angle_avg,'july_age':age,'snapshot_team':people[row.player_id].get('currentTeam',{}).get('name')})
        assert rob.signal_count(pd.DataFrame([row._asdict()]))[0] >= 2
    pd.DataFrame(evidence).to_csv(OUT/'player_raw_evidence.csv', index=False)
    # Same folds and preprocessing, but no edits to study.ALPHA or official forecasts.
    alpha_rows = []
    for alpha in [.1,1,10,100,1000]:
        pieces = []
        for year in study.DEV_YEARS+[2026]:
            train = features.loc[features.eligible_pair & features.target_season.lt(year)]
            test = features.loc[features.eligible & features.target_season.eq(year)].copy()
            assert train.target_season.max() < year
            for name, feature_cols in study.MODELS.items():
                model = make_pipeline(SimpleImputer(strategy='median'),StandardScaler(),Ridge(alpha=alpha))
                model.fit(train[feature_cols].to_numpy(dtype=float),train.target_woba.to_numpy(dtype=float))
                test['p_'+name] = model.predict(test[feature_cols].to_numpy(dtype=float))
            test['evaluation_scope'] = 'final_2026' if year == 2026 else 'development'
            pieces.append(test)
        p = pd.concat(pieces, ignore_index=True)
        if alpha == 10:
            a = p.set_index(['player_id','target_season'])
            b = predictions.set_index(['player_id','target_season'])
            for name in study.MODELS:
                assert np.allclose(a['p_'+name],b['p_'+name].reindex(a.index),rtol=0,atol=1e-10)
        for scope in ['development','final_2026']:
            d = p.loc[p.evaluation_scope.eq(scope) & p.target_available]
            for name in study.MODELS:
                error = d.target_woba-d['p_'+name]
                _, y, scores = rob.retention_data(p,scope)
                alpha_rows.append({'alpha':alpha,'scope':scope,'model':name,'n':len(d),'rmse':np.sqrt(np.mean(error**2)),'mae':np.mean(np.abs(error)),'retention_auc':roc_auc_score(y,scores[:,rob.MODELS.index(name)])})
    alpha_table = pd.DataFrame(alpha_rows)
    alpha_table.to_csv(OUT/'ridge_alpha_sensitivity.csv',index=False)
    m = alpha_table.pivot(index=['alpha','scope'], columns='model', values='mae')
    result['development_mae_M2_minus_M1'] = {str(a):float(m.loc[(a,'development'),'M2_levels']-m.loc[(a,'development'),'M1_results']) for a in [.1,1,10,100,1000]}
    s = pd.read_csv(ROOT/'reports/retention_sensitivity.csv')
    sums = rob.sensitivity_summary(s)
    sums.to_csv(OUT/'sensitivity_full_precision_summary.csv', index=False)
    result['sensitivity_summary'] = sums.to_dict('records')
    bt, names = rob.policy_backtest(predictions)
    gold = pd.read_csv(ROOT/'reports/scouting_policy_backtest.csv')
    columns = ['selected_n','growth_successes','usable_successes','available_n']
    assert np.allclose(bt[columns], gold[columns], atol=1e-10)
    decomposition = []
    overlap = []
    random_rows = []
    pmf_rows = []
    for policy in ['original_13','revised_hidden_5']:
        for method in ['signal_then_M1','M1_only']:
            d = names.loc[names.policy.eq(policy)&names.method.eq(method)]
            enough = d.target_pa.ge(200)
            growth = enough & d.target_woba.ge((d.predictor_woba+.020).round(3))
            decomposition.append({'policy':policy,'method':method,'slots':len(d),'unique_hitters':d.player_id.nunique(),'below_200pa':int((~enough).sum()),'sufficient_no_growth':int((enough&~growth).sum()),'growth_successes':int(growth.sum()),'available':int(enough.sum()),'growth_among_available':growth.sum()/enough.sum()})
        aa = names.loc[names.policy.eq(policy)&names.method.eq('signal_then_M1')]
        bb = names.loc[names.policy.eq(policy)&names.method.eq('M1_only')]
        shared = set(zip(aa.year,aa.player_id)) & set(zip(bb.year,bb.player_id))
        overlap.append({'policy':policy,'shared_player_seasons':len(shared)})
        pmf = np.array([1.])
        for year in study.DEV_YEARS+[2026]:
            pool = predictions.loc[predictions.target_season.eq(year)&predictions.discovery_pool]
            if policy == 'revised_hidden_5':pool = pool.loc[pool.delta_woba.lt(.020)]
            k = int(bt.loc[bt.year.eq(year)&bt.policy.eq(policy)&bt.method.eq('signal_then_M1'),'selected_n'].iloc[0])
            K = int(rob.decision_outcomes(pool)['growth'].sum())
            pmf = np.convolve(pmf,hypergeom.pmf(np.arange(k+1),len(pool),K,k))
        values = np.arange(len(pmf));cdf = np.cumsum(pmf)
        mean = float(values@pmf);sd=float(np.sqrt(((values-mean)**2)@pmf))
        for value,prob in enumerate(pmf):pmf_rows.append({'policy':policy,'growth_successes':value,'probability':float(prob)})
        for method in ['signal_then_M1','M1_only']:
            observed = int(bt.loc[bt.policy.eq(policy)&bt.method.eq(method),'growth_successes'].sum())
            random_rows.append({'policy':policy,'method':method,'observed':observed,'mean':mean,'sd':sd,'low':int(np.searchsorted(cdf,.025)),'high':int(np.searchsorted(cdf,.975)),'two_sided_probability_ordered_tail':float(pmf[pmf<=pmf[observed]+1e-12].sum()),'upper_tail':float(pmf[observed:].sum())})
    pd.DataFrame(decomposition).to_csv(OUT/'policy_loss_decomposition.csv',index=False)
    pd.DataFrame(overlap).to_csv(OUT/'policy_selection_overlap.csv',index=False)
    pd.DataFrame(random_rows).to_csv(OUT/'random_growth_benchmark.csv',index=False)
    pd.DataFrame(pmf_rows).to_csv(OUT/'random_growth_distribution.csv',index=False)
    result['random_benchmarks'] = random_rows
    power = []
    for n in [5,15,25]:
        threshold = next(x for x in range(n+1) if binom.sf(x-1,n,.24) <= .025)
        power.append({'n':n,'null_rate':.24,'alternative_rate':.4,'upper_tail_threshold':.025,'required_successes':threshold,'null_upper_tail':float(binom.sf(threshold-1,n,.24)),'power':float(binom.sf(threshold-1,n,.4))})
    pd.DataFrame(power).to_csv(OUT/'policy_power_illustration.csv',index=False)
    result['power'] = power
    (OUT/'verification_results.json').write_text(json.dumps(result,indent=2,ensure_ascii=False))
    print(json.dumps(result,indent=2,ensure_ascii=False))

if __name__ == '__main__':
    main()
