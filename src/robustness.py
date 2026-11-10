"""Exploratory robustness checks; never optimize thresholds against outcomes."""
from itertools import product
import numpy as np
import pandas as pd
from scipy.stats import hypergeom,spearmanr
from sklearn.metrics import roc_auc_score,balanced_accuracy_score

MODELS=['M1_results','M2_levels','M3_changes']
RISES=[.010,.020,.030]
LOSSES=[.000,.010,.020]
TARGET_PA=[100,200,300,400]

def signal_count(d):
    return np.column_stack([d.delta_exit_velocity.ge(.5),d.delta_barrel_pct.ge(1),d.delta_chase_pct.le(-1),d.delta_whiff_pct.le(-1)]).sum(axis=1)

def screen(d,hidden=False):
    ok=d.discovery_pool & d.xwoba.ge(.320) & d.delta_xwoba.ge(.010) & (signal_count(d)>=2)
    if hidden:ok=ok & d.delta_woba.lt(.020)
    return ok

def retention_data(predictions,scope,rise=.020,loss=.010,pa=200,view='conditional'):
    d=predictions.loc[predictions.evaluation_scope.eq(scope)&predictions.delta_woba.ge(rise)].copy().reset_index(drop=True)
    enough=d.target_pa.ge(pa)
    retained=d.target_woba.ge((d.woba-loss).round(3))
    if view=='conditional':
        d=d.loc[enough].copy().reset_index(drop=True)
        y=d.target_woba.ge((d.woba-loss).round(3)).astype(int).to_numpy()
    else:y=(enough&retained).astype(int).to_numpy()
    scores=np.column_stack([(d['p_'+m]-(d.woba-loss)).to_numpy() for m in MODELS])
    return d,y,scores

def sensitivity(predictions,scopes=('development','final_2026')):
    rows=[]
    for scope,rise,loss,pa,view in product(scopes,RISES,LOSSES,TARGET_PA,['conditional','all_followed_composite']):
        d,y,scores=retention_data(predictions,scope,rise,loss,pa,view)
        base=predictions.loc[predictions.evaluation_scope.eq(scope)&predictions.delta_woba.ge(rise)]
        for i,m in enumerate(MODELS):
            rows.append({'scope':scope,'rise':rise,'allowed_loss':loss,'target_pa_min':pa,'view':view,'model':m,'n':len(d),'unique_players':d.player_id.nunique(),'success_n':int(y.sum()),'full_breakout_cohort_n':len(base),'insufficient_pa_n':int(base.target_pa.lt(pa).sum()),'auc':roc_auc_score(y,scores[:,i]) if len(np.unique(y))==2 else np.nan,'balanced_accuracy':balanced_accuracy_score(y,(scores[:,i]>=0).astype(int)) if len(np.unique(y))==2 else np.nan,'main_definition':rise==.020 and loss==.010 and pa==200})
    return pd.DataFrame(rows)

def auc_uncertainty(predictions,scopes=('development','final_2026')):
    auc_rows=[];difference_rows=[]
    rng=np.random.default_rng(4427)
    for scope,view in product(scopes,['conditional','all_followed_composite']):
        d,y,scores=retention_data(predictions,scope,view=view)
        ids=d.player_id.unique();group={pid:np.flatnonzero(d.player_id.to_numpy()==pid) for pid in ids}
        if len(np.unique(y))<2:
            for m in MODELS:auc_rows.append({'scope':scope,'view':view,'model':m,'n':len(d),'unique_players':len(ids),'success_n':int(y.sum()),'auc':np.nan,'low':np.nan,'high':np.nan,'valid_resamples':0})
            for first,second in [(0,1),(1,2),(0,2)]:difference_rows.append({'scope':scope,'view':view,'comparison':MODELS[second]+' minus '+MODELS[first],'auc_gain':np.nan,'low':np.nan,'high':np.nan,'n':len(d),'unique_players':len(ids),'valid_resamples':0})
            continue
        observed=np.array([roc_auc_score(y,scores[:,i]) for i in range(3)])
        draws=[]
        for _ in range(1000):
            index=np.concatenate([group[pid] for pid in rng.choice(ids,size=len(ids),replace=True)])
            if len(np.unique(y[index]))<2:continue
            draws.append([roc_auc_score(y[index],scores[index,i]) for i in range(3)])
        draws=np.array(draws)
        for i,m in enumerate(MODELS):
            lo,hi=np.quantile(draws[:,i],[.025,.975])
            auc_rows.append({'scope':scope,'view':view,'model':m,'n':len(d),'unique_players':len(ids),'success_n':int(y.sum()),'auc':observed[i],'low':lo,'high':hi,'valid_resamples':len(draws)})
        for first,second in [(0,1),(1,2),(0,2)]:
            lo,hi=np.quantile(draws[:,second]-draws[:,first],[.025,.975])
            difference_rows.append({'scope':scope,'view':view,'comparison':MODELS[second]+' minus '+MODELS[first],'auc_gain':observed[second]-observed[first],'low':lo,'high':hi,'n':len(d),'unique_players':len(ids),'valid_resamples':len(draws)})
    return pd.DataFrame(auc_rows),pd.DataFrame(difference_rows)

def decision_outcomes(d):
    enough=d.target_pa.ge(200)
    return {'growth':enough&d.target_woba.ge((d.woba+.020).round(3)), 'usable':enough&d.target_woba.ge(.330), 'available':enough}

def policy_backtest(predictions,years=(2022,2023,2024,2025,2026)):
    rows=[];names=[]
    for year,policy in product(years,['original_13','revised_hidden_5']):
        d=predictions.loc[predictions.target_season.eq(year)&predictions.discovery_pool].copy()
        hidden=policy=='revised_hidden_5'
        if hidden:d=d.loc[d.delta_woba.lt(.020)]
        s=d.loc[screen(d,hidden)]
        k=min(5 if hidden else 13,len(s))
        methods={'signal_then_M1':(s,'p_M1_results'),'signal_then_delta_xwoba':(s,'delta_xwoba'),'M1_only':(d,'p_M1_results'),'current_woba':(d,'woba'),'current_xwoba':(d,'xwoba'),'delta_xwoba':(d,'delta_xwoba')}
        for method,(pool,col) in methods.items():
            selected=pool.sort_values([col,'player_id'],ascending=[False,True]).head(k)
            outcome=decision_outcomes(selected)
            rows.append({'year':year,'policy':policy,'method':method,'base_pool_n':len(d),'screen_pool_n':len(s),'selected_n':k,'growth_successes':int(outcome['growth'].sum()),'usable_successes':int(outcome['usable'].sum()),'available_n':int(outcome['available'].sum()),'mean_woba_available':selected.loc[outcome['available'],'target_woba'].mean(),'random_growth_low':np.nan,'random_growth_high':np.nan})
            for rank,r in enumerate(selected.itertuples(),1):
                names.append({'year':year,'policy':policy,'method':method,'rank':rank,'player_id':r.player_id,'name':r.display_name,'predictor_woba':r.woba,'target_pa':r.target_pa,'target_woba':r.target_woba})
        total=decision_outcomes(d)
        random={'year':year,'policy':policy,'method':'random_expected','base_pool_n':len(d),'screen_pool_n':len(s),'selected_n':k,'mean_woba_available':np.nan}
        for key,col in [('growth','growth_successes'),('usable','usable_successes'),('available','available_n')]:
            successes=int(total[key].sum());random[col]=k*successes/len(d) if len(d) else 0
            random['random_'+key+'_low']=float(hypergeom.ppf(.025,len(d),successes,k)) if k else 0.
            random['random_'+key+'_high']=float(hypergeom.ppf(.975,len(d),successes,k)) if k else 0.
        rows.append(random)
    return pd.DataFrame(rows),pd.DataFrame(names)

def policy_summary(backtest):
    rows=[]
    for (policy,method),d in backtest.groupby(['policy','method'],sort=False):
        rows.append({'policy':policy,'method':method,'total_slots':int(d.selected_n.sum()),'growth_successes':float(d.growth_successes.sum()),'usable_successes':float(d.usable_successes.sum()),'available_n':float(d.available_n.sum()),'years':len(d)})
    return pd.DataFrame(rows)

def ranking_churn(predictions,current):
    rows=[];names=[]
    periods={str(year):predictions.loc[predictions.target_season.eq(year)&predictions.discovery_pool] for year in [2022,2023,2024,2025,2026]}
    periods['2027_forecast']=current.loc[current.discovery_pool]
    for year,d in periods.items():
        ranks={m:d.sort_values(['p_'+m,'player_id'],ascending=[False,True]).reset_index(drop=True) for m in MODELS}
        for k,first,second in product([5,15],MODELS,MODELS):
            if (first,second) not in [('M1_results','M2_levels'),('M2_levels','M3_changes'),('M1_results','M3_changes')]:continue
            a=ranks[first].head(k);b=ranks[second].head(k);a_ids=set(a.player_id);b_ids=set(b.player_id)
            ra=ranks[first].assign(rank=np.arange(1,len(d)+1)).set_index('player_id')['rank']
            rb=ranks[second].assign(rank=np.arange(1,len(d)+1)).set_index('player_id')['rank'].reindex(ra.index)
            rows.append({'period':year,'k':k,'comparison':second+' vs '+first,'pool_n':len(d),'replacements':len(b_ids-a_ids),'jaccard':len(a_ids&b_ids)/len(a_ids|b_ids),'mean_absolute_rank_change':float(np.abs(ra-rb).mean()),'rank_spearman':spearmanr(ra,rb).statistic})
            for kind,group in [('added',b.loc[b.player_id.isin(b_ids-a_ids)]),('removed',a.loc[a.player_id.isin(a_ids-b_ids)])]:
                for r in group.itertuples():names.append({'period':year,'k':k,'comparison':second+' vs '+first,'change':kind,'player_id':r.player_id,'name':r.display_name})
    return pd.DataFrame(rows),pd.DataFrame(names)

def sensitivity_summary(s):
    rows=[]
    for (scope,view),d in s.groupby(['scope','view']):
        p=d.pivot(index=['rise','allowed_loss','target_pa_min'],columns='model',values='auc')
        for first,second in [('M1_results','M2_levels'),('M2_levels','M3_changes'),('M1_results','M3_changes')]:
            change=(p[second]-p[first]).dropna()
            rows.append({'scope':scope,'view':view,'comparison':second+' minus '+first,'definitions':len(change),'positive_definitions':int(change.gt(0).sum()),'min_auc_gain':change.min(),'median_auc_gain':change.median(),'max_auc_gain':change.max()})
    return pd.DataFrame(rows)
