"""Next-season hitter forecasting and a fully disclosed 2027 scouting watchlist."""
from pathlib import Path
from datetime import datetime, timezone
import json, hashlib
import numpy as np
import pandas as pd
from sklearn.pipeline import make_pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_squared_error, mean_absolute_error, roc_auc_score, balanced_accuracy_score
from .download import ROOT,RAW,YEARS

OUT=ROOT/'reports'
TRAD=['woba','prior_woba','age','age_squared','pa','prior_pa','k_percent','bb_percent','iso']
SKILLS=['xwoba','barrel_pct','hardhit_pct','exit_velocity','chase_pct','whiff_pct']
CHANGE=['delta_'+v for v in SKILLS]
MODELS={'M1_results':TRAD,'M2_levels':TRAD+SKILLS,'M3_changes':TRAD+SKILLS+CHANGE}
DEV_YEARS=[2022,2023,2024,2025]
ALPHA=10.0

def build_inputs():
    people={p['id']:p for f in sorted(RAW.glob('people_[0-9]*.json')) if not f.name.endswith('.meta.json') for p in json.loads(f.read_text())['people']}
    frames=[];checks=[]
    renames={'last_name, first_name':'name','home_run':'hr','batting_avg':'avg','slg_percent':'slg','on_base_percent':'obp','exit_velocity_avg':'exit_velocity','barrel_batted_rate':'barrel_pct','hard_hit_percent':'hardhit_pct','oz_swing_percent':'chase_pct','whiff_percent':'whiff_pct'}
    for year in YEARS:
        frame=pd.read_csv(RAW/f'custom_{year}.csv').rename(columns=renames)
        expected=pd.read_csv(RAW/f'expected_{year}.csv')
        assert frame.player_id.is_unique and expected.player_id.is_unique
        cross=frame.merge(expected[['player_id','pa','woba','est_woba']],on='player_id',suffixes=('','_official'),validate='one_to_one')
        assert len(cross)==len(frame)
        assert np.array_equal(cross.pa,cross.pa_official)
        assert np.allclose(cross.woba,cross.woba_official,atol=1e-9,equal_nan=True)
        assert np.allclose(cross.xwoba,cross.est_woba,atol=.00101,equal_nan=True)
        differences=int((~np.isclose(cross.xwoba,cross.est_woba,equal_nan=True)).sum())
        # The expected-statistics endpoint is canonical for the xwOBA level.
        frame['xwoba']=frame.player_id.map(expected.set_index('player_id').est_woba)
        frame['season']=year
        frame['age']=[(pd.Timestamp(year=year,month=7,day=1)-pd.Timestamp(people[int(pid)]['birthDate'])).days/365.2425 for pid in frame.player_id]
        frame['position']=[people[int(pid)]['primaryPosition']['abbreviation'] for pid in frame.player_id]
        frame['current_team']=[people[int(pid)].get('currentTeam',{}).get('name','Unknown') for pid in frame.player_id]
        frame['display_name']=[people[int(pid)]['fullName'] for pid in frame.player_id]
        frame['debut_date']=[people[int(pid)].get('mlbDebutDate','') for pid in frame.player_id]
        frame['age_squared']=frame.age**2
        frame['iso']=frame.slg-frame.avg
        frame['ops']=frame.obp+frame.slg
        valid=frame.woba.notna()&frame.pa.gt(0)
        frame['peer_woba']=np.average(frame.loc[valid,'woba'],weights=frame.loc[valid,'pa'])
        frame['source_regular_season']=True
        frames.append(frame)
        checks.append({'season':year,'players':len(frame),'pa':int(frame.pa.sum()),'eligible_200pa':int(frame.pa.ge(200).sum()),'official_expected_reconciliation':True,'low_pa_xwoba_rounding_differences':differences})
    all_seasons=pd.concat(frames,ignore_index=True)
    prior=all_seasons[['player_id','season','pa','woba']+SKILLS].copy()
    prior['season']+=1
    prior=prior.rename(columns={v:'prior_'+v for v in ['pa','woba']+SKILLS})
    features=all_seasons.merge(prior,on=['player_id','season'],how='left',validate='one_to_one')
    for v in SKILLS:features['delta_'+v]=(features[v]-features['prior_'+v]).round(6)
    features['delta_woba']=(features.woba-features.prior_woba).round(3)
    features['xwoba_gap']=features.xwoba-features.woba
    features['short_prior_season']=features.season.eq(2021)
    features['eligible']=features.pa.ge(200)&features.prior_pa.ge(100)&features.season.ne(2020)
    features['modest_results']=features.woba.le(features.peer_woba+0.020)&features.hr.le(25)
    # Refinement documented after seeing the first production-only 2027 names.
    # Only past/current performance determines eligibility, never future outcomes.
    flags=[]
    for row in features.itertuples():
        past=all_seasons.loc[all_seasons.player_id.eq(row.player_id)&all_seasons.season.between(row.season-2,row.season-1)&all_seasons.pa.ge(200)]
        flags.append(bool(past.woba.ge(.360).any()))
    features['recent_high_production']=flags
    features['discovery_pool']=features.modest_results&~features.recent_high_production
    targets=all_seasons[['player_id','season','pa','woba']].copy()
    targets['season']-=1
    targets=targets.rename(columns={'pa':'target_pa','woba':'target_woba'})
    features=features.merge(targets,on=['player_id','season'],how='left',validate='one_to_one')
    features['target_season']=features.season+1
    completed=features.season.le(2025)
    features.loc[completed,'target_pa']=features.loc[completed,'target_pa'].fillna(0)
    features['target_available']=features.target_pa.ge(200)
    features['eligible_pair']=features.eligible&features.target_available&features.target_season.le(2026)&features.target_season.ne(2020)
    # Verify complete 2026 PA at the individual player level against MLB's season totals.
    splits=json.loads((RAW/'mlb_hitting_2026.json').read_text())['stats'][0]['splits']
    official={x['player']['id']:int(x['stat']['plateAppearances']) for x in splits}
    current=features.loc[features.season.eq(2026)]
    pa_check=current[['player_id','display_name','pa']].copy()
    pa_check['mlb_pa']=pa_check.player_id.map(official)
    assert pa_check.mlb_pa.notna().all()
    pa_check['difference']=pa_check.pa-pa_check.mlb_pa
    assert pa_check.difference.abs().max()<=1
    discrepancies=pa_check.loc[pa_check.difference.ne(0)]
    discrepancies.to_csv(OUT/'2026_pa_source_discrepancies.csv',index=False)
    assert int(current.pa.sum())==sum(official.values())
    schedule=json.loads((RAW/'schedule_2026.json').read_text())
    games=[g for day in schedule['dates'] for g in day['games'] if g['gameType']=='R']
    completed_games=[g for g in games if g['status']['abstractGameState']=='Final']
    end=max(day['date'] for day in schedule['dates'] if any(g['status']['abstractGameState']=='Final' for g in day['games']))
    future_known=[g for g in games if g['status']['abstractGameState']!='Final' and g['status'].get('detailedState') not in ['Cancelled','Canceled','Postponed']]
    assert not future_known, 'Regular season not complete'
    pd.DataFrame(checks).to_csv(OUT/'data_audit.csv',index=False)
    all_seasons.to_csv(ROOT/'data/processed/hitter_seasons.csv',index=False)
    features.to_csv(ROOT/'data/processed/features.csv',index=False)
    return features,{'regular_season_end':end,'completed_regular_games':len(completed_games),'pa_2026':int(current.pa.sum()),'mlb_total_pa_reconciliation':True,'mlb_individual_pa_discrepancies':len(discrepancies),'max_individual_pa_difference':int(pa_check.difference.abs().max()),'individual_discrepancy_reason':'Not established; preserve Savant measurements consistently and disclose feed differences.','source_files':len(list(RAW.glob('*.meta.json')))}

def fit_model(train,features):
    model=make_pipeline(SimpleImputer(strategy='median'),StandardScaler(),Ridge(alpha=ALPHA))
    model.fit(train[features].to_numpy(dtype=float),train.target_woba.to_numpy(dtype=float))
    return model

def evaluate(features):
    pieces=[];coef=[]
    for year in DEV_YEARS+[2026]:
        train=features.loc[features.eligible_pair&features.target_season.lt(year)]
        test=features.loc[features.eligible&features.target_season.eq(year)].copy()
        assert train.target_season.max()<year
        test['p_B0_carry']=test.woba
        test['evaluation_scope']='final_2026' if year==2026 else 'development'
        test['train_n']=len(train)
        for name,cols in MODELS.items():
            model=fit_model(train,cols)
            test['p_'+name]=model.predict(test[cols].to_numpy(dtype=float))
            for col,value in zip(cols,model.named_steps['ridge'].coef_):
                coef.append({'target_year':year,'model':name,'feature':col,'standardized_coefficient':float(value)})
        pieces.append(test)
    return pd.concat(pieces,ignore_index=True),pd.DataFrame(coef)

def metric_table(predictions):
    rows=[]
    scopes={'development':predictions.loc[predictions.evaluation_scope.eq('development')], 'final_2026':predictions.loc[predictions.target_season.eq(2026)],'without_2022':predictions.loc[predictions.target_season.isin([2023,2024,2025])]}
    scopes.update({str(year):predictions.loc[predictions.target_season.eq(year)] for year in DEV_YEARS})
    for scope,frame in scopes.items():
        frame=frame.loc[frame.target_available]
        for name in ['B0_carry']+list(MODELS):
            p=frame['p_'+name];y=frame.target_woba
            rows.append({'scope':scope,'model':name,'n':len(frame),'rmse':float(np.sqrt(np.mean((y-p)**2))),'mae':float(np.mean(np.abs(y-p))),'pa_weighted_rmse':float(np.sqrt(np.average((y-p)**2,weights=frame.target_pa)))})
    return pd.DataFrame(rows)

def selection_rule(metrics):
    dev=metrics.loc[metrics.scope.eq('development')].set_index('model')
    final=metrics.loc[metrics.scope.eq('final_2026')].set_index('model')
    positive_years=sum(metrics.loc[(metrics.scope.eq(str(y)))&metrics.model.eq('M3_changes'),'rmse'].iloc[0]<metrics.loc[(metrics.scope.eq(str(y)))&metrics.model.eq('M2_levels'),'rmse'].iloc[0] for y in DEV_YEARS)
    changes={'development_rmse_improves':bool(dev.loc['M3_changes','rmse']<dev.loc['M2_levels','rmse']),'development_mae_improves':bool(dev.loc['M3_changes','mae']<dev.loc['M2_levels','mae']),'positive_development_years':int(positive_years),'final_2026_rmse_improves':bool(final.loc['M3_changes','rmse']<final.loc['M2_levels','rmse'])}
    support=changes['development_rmse_improves'] and changes['development_mae_improves'] and positive_years>=3 and changes['final_2026_rmse_improves']
    levels=bool(dev.loc['M2_levels','rmse']<dev.loc['M1_results','rmse'] and dev.loc['M2_levels','mae']<dev.loc['M1_results','mae'] and final.loc['M2_levels','rmse']<final.loc['M1_results','rmse'])
    selected='M3_changes' if support else ('M2_levels' if levels else 'M1_results')
    return {'selected_model':selected,'support_changes':bool(support),'changes_checks':changes,'levels_supported':levels,'selection_disclosure':'Exploratory development policy includes final-2026 performance. That comparison is not a second untouched holdout for the resulting selection.'}

def paired_gain(predictions,first,second):
    d=predictions.loc[predictions.evaluation_scope.eq('development')&predictions.target_available].copy()
    d['gain']=(d.target_woba-d['p_'+first])**2-(d.target_woba-d['p_'+second])**2
    rng=np.random.default_rng(1701)
    intervals={}
    for group in ['target_season','player_id']:
        sums=d.groupby(group)['gain'].sum().to_numpy();counts=d.groupby(group).size().to_numpy()
        indexes=rng.integers(0,len(sums),size=(3000,len(sums)))
        draws=sums[indexes].sum(axis=1)/counts[indexes].sum(axis=1)
        intervals[group]=np.quantile(draws,[.025,.975]).tolist()
    return {'comparison':first+' → '+second,'mean_squared_error_gain':float(d.gain.mean()),'exploratory_cluster_95pct_intervals':intervals,'by_target_year':{str(k):float(v) for k,v in d.groupby('target_season').gain.mean().items()}}

def decision_backtest(predictions):
    rows=[];names=[]
    for year in DEV_YEARS+[2026]:
      for pool_name,pool_column in [('modest_results','modest_results'),('discovery_pool','discovery_pool')]:
        candidates=predictions.loc[predictions.target_season.eq(year)&predictions[pool_column]]
        for name,column in {'visible_woba':'woba','xwoba':'xwoba',**{name:'p_'+name for name in MODELS}}.items():
            selected=candidates.sort_values([column,'player_id'],ascending=[False,True]).head(15).copy()
            usable=selected.target_available&selected.target_woba.ge(.330)
            valid=selected.loc[selected.target_available]
            rows.append({'target_year':year,'pool':pool_name,'method':name,'candidate_pool':len(candidates),'selected_n':len(selected),'available_200pa':int(selected.target_available.sum()),'usable_bat_successes':int(usable.sum()),'usable_bat_rate':float(usable.mean()),'mean_target_woba_available':float(valid.target_woba.mean())})
            for rank,row in enumerate(selected.itertuples(),1):
                names.append({'target_year':year,'pool':pool_name,'method':name,'rank':rank,'player_id':row.player_id,'name':row.display_name,'predictor_woba':row.woba,'predictor_xwoba':row.xwoba,'target_pa':row.target_pa,'target_woba':row.target_woba,'target_available':row.target_available,'usable_bat':bool(row.target_available and row.target_woba>=.330)})
    return pd.DataFrame(rows),pd.DataFrame(names)

def breakout_diagnostics(predictions):
    rows=[]
    for scope in ['development','final_2026']:
        d=predictions.loc[predictions.evaluation_scope.eq(scope)&predictions.target_available&predictions.delta_woba.ge(.020)]
        y=(d.target_woba>=(d.woba-.010).round(3)).astype(int)
        for name in MODELS:
            margin=d['p_'+name]-(d.woba-.010)
            rows.append({'scope':scope,'model':name,'n_apparent_breakouts':len(d),'sustained_n':int(y.sum()),'retention_margin_auc':float(roc_auc_score(y,margin)) if y.nunique()==2 else None,'threshold_accuracy':float(((margin>=0).astype(int)==y).mean()),'balanced_accuracy':float(balanced_accuracy_score(y,(margin>=0).astype(int)))})
    return pd.DataFrame(rows)

def forecast(features,predictions,policy):
    current=features.loc[features.season.eq(2026)&features.eligible].copy()
    assert current.target_woba.isna().all()
    train=features.loc[features.eligible_pair&features.target_season.le(2026)]
    for name,cols in MODELS.items():current['p_'+name]=fit_model(train,cols).predict(current[cols].to_numpy(dtype=float))
    selected=policy['selected_model']
    current['projected_woba_2027']=current['p_'+selected]
    current['projected_delta']=current.projected_woba_2027-current.woba
    current['model_spread']=current[['p_'+name for name in MODELS]].max(axis=1)-current[['p_'+name for name in MODELS]].min(axis=1)
    residuals=predictions.loc[predictions.target_available,'target_woba']-predictions.loc[predictions.target_available,'p_'+selected]
    low,high=np.quantile(residuals,[.10,.90])
    current['exploratory_80pct_low']=current.projected_woba_2027+low
    current['exploratory_80pct_high']=current.projected_woba_2027+high
    current['type']=np.where(current.delta_woba.le(-.010),'회복 후보','성장 관찰 후보')
    improving=np.column_stack([current.delta_exit_velocity.ge(.5),current.delta_barrel_pct.ge(1),current.delta_chase_pct.le(-1),current.delta_whiff_pct.le(-1)])
    current['improving_signal_count']=improving.sum(axis=1)
    current['salary_2027_status']='미확인 — 계약·옵션·영입 비용 별도 조사'
    current['created_at_utc']=datetime.now(timezone.utc).isoformat()
    watch=current.loc[current.discovery_pool].sort_values(['projected_woba_2027','player_id'],ascending=[False,True]).head(15).copy()
    watch.insert(0,'rank',np.arange(1,len(watch)+1))
    # Block-player resampling: descriptive coefficient/ranking stability, not breakout probability.
    candidate=current.loc[current.discovery_pool].copy()
    ids=train.player_id.unique();groups={pid:group for pid,group in train.groupby('player_id')}
    rng=np.random.default_rng(2027);draws=[]
    for _ in range(150):
        boot=pd.concat([groups[pid] for pid in rng.choice(ids,size=len(ids),replace=True)],ignore_index=True)
        p=fit_model(boot,MODELS[selected]).predict(candidate[MODELS[selected]].to_numpy(dtype=float))
        ranks=pd.Series(p,index=candidate.player_id).rank(ascending=False,method='first')
        draws.append(ranks)
    ranks=pd.DataFrame(draws)
    stability=pd.DataFrame({'player_id':ranks.columns,'bootstrap_top15_share':(ranks<=15).mean().to_numpy(),'bootstrap_median_rank':ranks.median().to_numpy()})
    watch=watch.merge(stability,on='player_id',validate='one_to_one')
    coverage=float(((residuals>=low)&(residuals<=high)).mean())
    return current,watch,{'residual_quantiles':[float(low),float(high)],'historical_empirical_coverage':coverage,'interpretation':'Exploratory historical error range; future calibrated coverage and breakout probability are not established.'}

def run():
    OUT.mkdir(exist_ok=True)
    print('1/4 Reconcile official season inputs',flush=True)
    features,audit=build_inputs()
    print('2/4 Expanding-year validation, then final target year 2026',flush=True)
    predictions,coefficients=evaluate(features)
    metrics=metric_table(predictions);policy=selection_rule(metrics)
    gains=[paired_gain(predictions,'M1_results','M2_levels'),paired_gain(predictions,'M2_levels','M3_changes')]
    backtest,names=decision_backtest(predictions)
    diagnostics=breakout_diagnostics(predictions)
    print('3/4 Fit completed history and build 2027 research watchlist',flush=True)
    current,watch,bands=forecast(features,predictions,policy)
    tables={'historical_predictions.csv':predictions,'model_metrics.csv':metrics,'coefficients.csv':coefficients,'decision_backtest.csv':backtest,'decision_backtest_names.csv':names,'breakout_diagnostics.csv':diagnostics,'2027_all_forecasts.csv':current,'2027_watchlist.csv':watch}
    for name,frame in tables.items():frame.to_csv(OUT/name,index=False)
    manifest={'project':'Signals for Next Season','forecast_year':2027,'input_season':2026,'as_of_utc':datetime.now(timezone.utc).isoformat(),'audit':audit,'policy':policy,'gains':gains,'bands':bands,'primary_future_outcomes':'2027 pending; no fabricated labels','code_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'protocol_sha256':hashlib.sha256((ROOT/'docs/PROTOCOL.md').read_bytes()).hexdigest(),'training_pairs':int(features.eligible_pair.sum()),'development_labeled_n':int((predictions.evaluation_scope.eq('development')&predictions.target_available).sum()),'final_2026_labeled_n':int((predictions.target_season.eq(2026)&predictions.target_available).sum()),'2026_main_forecast_n':len(current),'2026_low_history_200pa_n':int((features.season.eq(2026)&features.pa.ge(200)&~features.eligible).sum())}
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
    pending=watch[['rank','player_id','display_name','projected_woba_2027','created_at_utc']].copy()
    pending['actual_pa_2027']=np.nan;pending['actual_woba_2027']=np.nan;pending['status']='pending'
    pending.to_csv(OUT/'2027_outcome_log.csv',index=False)
    print(metrics.loc[metrics.scope.isin(['development','final_2026'])].to_string(index=False),flush=True)
    print(json.dumps(policy,ensure_ascii=False),flush=True)
    print(watch[['rank','display_name','type','woba','xwoba','projected_woba_2027','projected_delta','bootstrap_top15_share']].to_string(index=False),flush=True)
    print('4/4 Study complete; frozen 2027 forecasts saved.',flush=True)

if __name__=='__main__':run()
