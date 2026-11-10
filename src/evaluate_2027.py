"""Evaluate frozen predictions only after complete 2027 regular-season outcomes."""
from pathlib import Path
import argparse,hashlib,json
from datetime import datetime,timezone
import numpy as np
import pandas as pd
from .download import ROOT
from .robustness import sensitivity,auc_uncertainty,policy_backtest,policy_summary,MODELS

def load_outcomes(path):
    d=pd.read_csv(path)
    needed={'player_id','season','pa','woba'}
    if not needed.issubset(d):raise ValueError('Required columns: player_id, season, pa, woba')
    if d.empty or not d.season.eq(2027).all():raise ValueError('Only nonempty complete 2027 regular-season data are accepted')
    if not d.player_id.is_unique:raise ValueError('Duplicate MLB player IDs')
    if d.pa.isna().any() or d.pa.lt(0).any() or not np.equal(d.pa,np.floor(d.pa)).all():raise ValueError('PA must be nonnegative integers')
    if (d.pa.gt(0)&d.woba.isna()).any():raise ValueError('Positive-PA hitters require recorded wOBA')
    # wOBA is a weighted rate, not a probability; tiny-PA hitters can exceed 1.
    recorded=d.loc[d.woba.notna(),'woba']
    if not (np.isfinite(recorded)&recorded.ge(0)).all():raise ValueError('wOBA must be finite and nonnegative')
    return d

def evaluate_frame(frozen,outcomes):
    frame=frozen.drop(columns=['target_pa','target_woba'],errors='ignore').merge(outcomes[['player_id','pa','woba']].rename(columns={'pa':'target_pa','woba':'target_woba'}),on='player_id',how='left',validate='one_to_one')
    frame['target_pa']=frame.target_pa.fillna(0)
    frame['target_season']=2027;frame['evaluation_scope']='prospective_2027';frame['target_available']=frame.target_pa.ge(200)
    enough=frame.loc[frame.target_available];metrics=[]
    for model,col in [('B0_carry','woba')]+[(m,'p_'+m) for m in MODELS]:
        e=enough.target_woba-enough[col]
        metrics.append({'scope':'prospective_2027','model':model,'n':len(enough),'unique_players':enough.player_id.nunique(),'rmse':np.sqrt((e**2).mean()),'mae':e.abs().mean(),'pa_weighted_rmse':np.sqrt(np.average(e**2,weights=enough.target_pa)) if len(enough) else np.nan})
    sens=sensitivity(frame,scopes=['prospective_2027']);auc,paired=auc_uncertainty(frame,scopes=['prospective_2027'])
    backtest,names=policy_backtest(frame,years=[2027])
    return {'evaluated_cohort.csv':frame,'prospective_metrics.csv':pd.DataFrame(metrics),'retention_sensitivity.csv':sens,'auc_intervals.csv':auc,'paired_auc_intervals.csv':paired,'scouting_policy_backtest.csv':backtest,'scouting_policy_names.csv':names,'scouting_policy_summary.csv':policy_summary(backtest)}

def run():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--outcomes',type=Path,required=True)
    p.add_argument('--season-complete',action='store_true',help='Assert full regular season; never use this for a partial feed')
    p.add_argument('--source',required=True,help='Official outcome source URL or dataset description')
    p.add_argument('--output',type=Path,default=ROOT/'prospective_results_2027')
    args=p.parse_args()
    if not args.season_complete:raise SystemExit('Evaluation blocked: explicitly confirm complete 2027 regular season with --season-complete')
    lock=json.loads((ROOT/'reports/2027_evaluation_lock.json').read_text())
    for rel,expected in lock['sha256'].items():
        if hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()!=expected:raise SystemExit('Frozen file changed: '+rel)
    frozen=pd.read_csv(ROOT/'reports/2027_frozen_evaluation.csv');outcomes=load_outcomes(args.outcomes)
    tables=evaluate_frame(frozen,outcomes)
    if args.output.exists() and any(args.output.iterdir()):raise SystemExit('Choose an empty output directory; do not overwrite earlier evaluations')
    args.output.mkdir(parents=True,exist_ok=True)
    for name,frame in tables.items():frame.to_csv(args.output/name,index=False)
    audit={'evaluated_at_utc':datetime.now(timezone.utc).isoformat(),'source':args.source,'outcomes_sha256':hashlib.sha256(args.outcomes.read_bytes()).hexdigest(),'frozen_lock':lock,'absent_players':'PA=0 only because complete season was explicitly confirmed','models_refit':False}
    (args.output/'evaluation_manifest.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2))
    print(tables['prospective_metrics.csv'].to_string(index=False))
    print('Completed fixed prospective evaluation:',args.output)

if __name__=='__main__':run()
