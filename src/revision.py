"""Revised annual scouting study and a genuinely future evaluation commitment."""
from pathlib import Path
from datetime import datetime,timezone
import base64,hashlib,html,json,re,zipfile
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from .download import ROOT
from . import robustness as rob

OUT=ROOT/'reports'
TITLE='Signals for Next Season'

def table(d):return '<div class="table-wrap">'+d.to_html(index=False,border=0,escape=True)+'</div>'
def picture(name):return '<img class="chart" src="data:image/png;base64,'+base64.b64encode((OUT/name).read_bytes()).decode()+'" alt="'+html.escape(name)+'">'
def number(x):return f'{x:.3f}'
def section_replace(report,pattern,body):
    result,n=re.subn(pattern,lambda _:body,report,count=1,flags=re.S)
    assert n==1,pattern
    return result

def freeze(current):
    path=OUT/'2027_evaluation_lock.json'
    if path.exists():
        lock=json.loads(path.read_text())
        for rel,h in lock['sha256'].items():assert hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()==h,'Frozen evaluation changed: '+rel
        return lock
    assert current.target_woba.isna().all() and current.target_pa.isna().all()
    frozen=current.copy();frozen['target_pa']=np.nan;frozen['target_woba']=np.nan
    frozen['actual_pa_2027']=np.nan;frozen['actual_woba_2027']=np.nan;frozen['evaluation_status']='pending'
    frozen['apparent_breakout_2026']=frozen.delta_woba.ge(.020)
    selections={}
    for policy,hidden,budget in [('original_13',False,13),('revised_hidden_5',True,5)]:
        base=frozen.loc[frozen.discovery_pool & (frozen.delta_woba.lt(.020) if hidden else True)]
        screened=base.loc[rob.screen(base,hidden)]
        k=min(budget,len(screened));choices={}
        for name,(pool,col) in {'signal_then_M1':(screened,'p_M1_results'),'signal_then_delta_xwoba':(screened,'delta_xwoba'),'M1_only':(base,'p_M1_results'),'current_woba':(base,'woba'),'current_xwoba':(base,'xwoba'),'delta_xwoba':(base,'delta_xwoba')}.items():
            ids=pool.sort_values([col,'player_id'],ascending=[False,True]).head(k).player_id.tolist()
            choices[name]=ids;frozen[policy+'_'+name]=frozen.player_id.isin(ids)
        selections[policy]={'k':k,'random_base_pool_ids':base.player_id.tolist(),'selected_ids':choices}
    frozen.to_csv(OUT/'2027_frozen_evaluation.csv',index=False)
    files=['docs/PROSPECTIVE_2027_PROTOCOL.md','reports/2027_frozen_evaluation.csv','src/robustness.py','src/evaluate_2027.py']
    lock={'project':TITLE,'locked_at_utc':datetime.now(timezone.utc).isoformat(),'original_forecast_at_utc':current.created_at_utc.iloc[0],'historical_status':'2022–2026 already observed; all revised historical analyses exploratory','prospective_target':2027,'selected_projection':'M1_results','primary':'conditional next-season wOBA RMSE and MAE, target PA>=200','secondary':'breakout rise>=.020; retained within .010; target PA>=200; preserved as secondary','forecast_players':len(frozen),'selection_policies':selections,'sha256':{rel:hashlib.sha256((ROOT/rel).read_bytes()).hexdigest() for rel in files}}
    path.write_text(json.dumps(lock,ensure_ascii=False,indent=2),encoding='utf-8')
    return lock

def figures(auc,current,queue):
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(1,2,figsize=(10,4),layout='constrained')
    for scope,ax,title in zip(['development','final_2026'],axes,['Observed tests: 2022–2025','Observed test: 2026']):
        d=auc.loc[auc.scope.eq(scope)&auc.view.eq('conditional')].set_index('model').loc[rob.MODELS]
        ax.bar(['M1','M2','M3'],d.auc,color=['#617786','#2b918d','#e59b42'])
        ax.errorbar(np.arange(3),d.auc,yerr=np.array([d.auc-d.low,d.high-d.auc]),fmt='none',color='#243d4b',capsize=5)
        ax.axhline(.5,ls='--',lw=1,color='#aab6bd');ax.set_ylim(0,1);ax.set_ylabel('Retention AUC · exploratory 95% range');ax.set_title(title,fontweight='bold')
        for i,r in enumerate(d.itertuples()):ax.text(i,r.high+.025,f'{r.auc:.3f}',ha='center')
    fig.savefig(OUT/'retention_with_uncertainty.png',dpi=180);plt.close(fig)
    fig,ax=plt.subplots(figsize=(9,6),layout='constrained')
    d=current.loc[current.discovery_pool]
    ax.scatter(d.delta_woba,d.delta_xwoba,s=26,color='#b5c4cd',alpha=.6,label='Discovery proxy pool')
    ax.scatter(queue.delta_woba,queue.delta_xwoba,s=50,color='#2b918d',label='Five experimental hypotheses')
    ax.axhline(0,color='#b5c4cd',lw=1);ax.axvline(0,color='#b5c4cd',lw=1)
    ax.axvline(.020,color='#e59b42',lw=1,ls='--',label='Already-apparent breakout cutoff')
    for name,shift in {'Heriberto Hernández':(-40,14),'Spencer Steer':(-35,12),'Lars Nootbaar':(10,-18),'Kyle Karros':(-50,10),'Lawrence Butler':(-95,16)}.items():
        r=d.loc[d.display_name.eq(name)].iloc[0]
        ax.annotate(name,(r.delta_woba,r.delta_xwoba),xytext=shift,textcoords='offset points',fontsize=9)
    ax.set_xlabel('2025 → 2026 actual wOBA change');ax.set_ylabel('2025 → 2026 xwOBA change')
    ax.set_title('Underlying changes are hypotheses, not a validated priority queue',fontweight='bold',fontsize=13)
    ax.legend(fontsize=9,loc='lower right');ax.grid(alpha=.15)
    fig.savefig(OUT/'signal_divergence.png',dpi=180);plt.close(fig)

def prepare_queue(current):
    from .deliver import NOTES
    old=current.loc[rob.screen(current)].sort_values(['p_M1_results','player_id'],ascending=[False,True]).copy()
    old['group']=np.where(old.delta_woba.ge(.020),'이미 성적이 오른 유지 관찰 그룹','덜 드러난 변화 가설')
    old.to_csv(OUT/'2027_original_screen_groups.csv',index=False)
    queue=old.loc[old.delta_woba.lt(.020)].copy()
    queue.insert(0,'queue_order',np.arange(1,len(queue)+1))
    for col,index in [('review_priority',0),('hypothesis',1),('supporting_evidence',2),('opposing_evidence',3),('next_action',4)]:queue[col]=queue.display_name.map(lambda x:NOTES[x][index])
    queue['review_priority']='실험적 조사 가설 — M1 기준보다 우선하지 않음'
    queue['screen_status']='Post-results revised screen; retrospective growth yield lower than M1-only'
    queue.to_csv(OUT/'2027_scouting_queue.csv',index=False)
    pending=queue[['queue_order','player_id','display_name','projected_woba_2027','created_at_utc']].copy()
    pending['actual_pa_2027']=np.nan;pending['actual_woba_2027']=np.nan;pending['status']='pending'
    pending.to_csv(OUT/'2027_scouting_outcome_log.csv',index=False)
    return queue,old

def report(current,queue,old,auc,paired,sensitivity,summary,churn,backtest,lock):
    old_path=OUT/'Before_the_Box_Score_2027_Report.html'
    template=old_path.read_text() if old_path.exists() else (OUT/'Signals_for_Next_Season_2027_Report.html').read_text()
    style=re.search(r'<style>(.*?)</style>',template,re.S).group(1)
    intro=f'''<header><div class="eyebrow">JUHAN YOUN · MSBA ANALYTICS PORTFOLIO · REVISED 2026 → 2027</div><h1>{TITLE}</h1><p class="subtitle">2026 타격 지표로 평가하는 2027 전망과 스카우팅 조사 정책</p><p class="meta">2026 전체 정규시즌 · 타자 · 조기 발견을 검증하는 연구가 아닌 연간 전망 연구<br>원래 전망 고정: {html.escape(lock['original_forecast_at_utc'])} · 2027 평가 규칙 고정: {html.escape(lock['locked_at_utc'])}</p></header>'''
    template=section_replace(template,r'<header>.*?</header>',intro)
    lead='''<section class="lead"><h2>결론: 좋은 신호와 좋은 선택 정책은 다르다</h2><p><strong>현재 타격 질을 더한 모델은 관측된 breakout 유지 구분에서 전통적 모델보다 높은 AUC를 보였다. 전년 대비 변화가 현재 수준 위에 더하는 효과는 작고 일관적이지 않았다.</strong></p><p>신호가 좋은 선수만 먼저 고르는 기존 조사 규칙은 과거 동일 예산 비교에서 성장 성공 7/53건으로 M1 단독의 13/53건보다 낮았다. 이미 오른 선수를 제외한 새 조사 규칙도 2/22건, M1 단독은 7/22건이었다. <strong>따라서 신호 screen을 더 효율적인 스카우팅 순위로 채택하지 않는다.</strong> M1 전망을 기준 자료로 두고 변화 정보는 개별 가설의 진단에 사용한다.</p><p>2022–2026 결과는 이미 관측한 탐색적 증거다. 2026 평가를 모델 선택에도 썼으므로 독립 검증으로 제시하지 않는다. 다음 독립적인 시간 검증은 고정된 규칙·선수·전망으로 수행할 <strong>2027 전체 시즌 평가</strong>다. 연구 계획은 이번 문서에 날짜·해시와 함께 고정했다.</p></section>'''
    template=section_replace(template,r'<section class="lead">.*?</section>',lead)
    question='''<section id="question"><div class="eyebrow">01 · DECISION & ANALYTICAL QUESTION</div><h2>Which signals should inform next-season scouting?</h2><blockquote>Do current underlying skills and year-to-year changes improve next-season batting forecasts and breakout-retention assessment beyond traditional results?</blockquote><p>실제 결정은 제한된 영상 조사 시간을 어떤 선수에게 사용할지다. 원래의 조기 발견 질문은 연간 데이터가 검증한 범위보다 넓어 메인 제목·질문에서 제외했다. 본문은 시즌 종료 후 다음 해 전망과 조사 정책을 다룬다.</p><p>주 분석은 다음 시즌 실제 wOBA 예측이다. 성적 급상승의 유지 분류는 <strong>사전에 명시했던 보조 질문으로 유지</strong>하며, 더 좋은 수치가 나왔다는 이유로 주 분석으로 승격하지 않는다. 조사 정책 비교는 비판을 반영해 추가한 탐색적 분석이다. 수비·주루·출장량·계약 가격을 포함한 전체 영입 가치는 평가하지 않는다.</p></section>'''
    template=section_replace(template,r'<section id="question">.*?</section>',question)
    a=auc.copy();a['기간']=a.scope.map({'development':'2022–2025','final_2026':'2026'})
    a['관측 대상']=a.view.map({'conditional':'충분한 PA 조건','all_followed_composite':'전체 추적: PA+유지'})
    a['모델']=a.model.str.split('_').str[0];a['AUC']=a.auc.map(number);a['탐색적 95% 범위']=[f'{lo:.3f}–{hi:.3f}' for lo,hi in zip(a.low,a.high)]
    auc_table=table(a[['기간','관측 대상','모델','n','unique_players','success_n','AUC','탐색적 95% 범위']].rename(columns={'n':'관측 건수','unique_players':'선수 수','success_n':'유지 성공'}))
    p=paired.copy();p['기간']=p.scope.map({'development':'2022–2025','final_2026':'2026'});p['관측 대상']=p.view.map({'conditional':'PA 조건','all_followed_composite':'전체 추적'})
    p['비교']=p.comparison.replace({'M2_levels minus M1_results':'M2 − M1','M3_changes minus M2_levels':'M3 − M2','M3_changes minus M1_results':'M3 − M1'})
    p['차이']=p.auc_gain.map(lambda x:f'{x:+.3f}');p['탐색적 95% 범위']=[f'[{lo:+.3f}, {hi:+.3f}]' for lo,hi in zip(p.low,p.high)]
    paired_table=table(p[['기간','관측 대상','비교','차이','탐색적 95% 범위']])
    s=rob.sensitivity_summary(sensitivity);ss=s.copy();ss['기간']=ss.scope.map({'development':'2022–2025','final_2026':'2026'});ss['대상']=ss.view.map({'conditional':'PA 조건','all_followed_composite':'전체 추적'})
    ss['비교']=ss.comparison.replace({'M2_levels minus M1_results':'M2 − M1','M3_changes minus M2_levels':'M3 − M2','M3_changes minus M1_results':'M3 − M1'})
    ss['양의 차이 정의 수']=[f'{n}/{total}' for n,total in zip(ss.positive_definitions,ss.definitions)]
    ss['AUC 차이 최솟값–최댓값']=[f'{lo:+.3f}–{hi:+.3f}' for lo,hi in zip(ss.min_auc_gain,ss.max_auc_gain)]
    sens_html=table(ss[['기간','대상','비교','양의 차이 정의 수','AUC 차이 최솟값–최댓값']])
    full=sensitivity.pivot(index=['scope','view','rise','allowed_loss','target_pa_min','n','unique_players','success_n'],columns='model',values='auc').reset_index()
    for m in rob.MODELS:full[m]=full[m].map(number)
    sec=f'''<section><div class="eyebrow">04 · SECONDARY QUESTION, WITH ROBUSTNESS</div><h2>유지 구분: 표본·짝지은 비교·정의 변화</h2><p>기본 정의는 wOBA 상승 ≥.020, 다음 해 손실 ≤.010, 다음 해 PA ≥200이다. 운영상 정의로서 야구적 진리나 유일한 기준이 아니다.</p><p><strong>반복 관측:</strong> 개발 조건부 진단 250건은 206명의 기록이다. 전체 breakout 추적은 292건·243명으로, 42건이 다음 해 200PA를 얻지 못했다. 2026은 86명 중 66명만 200PA 이상이며 20명이 제외된다. 이 차이를 숨기지 않는다.</p>{auc_table}{picture('retention_with_uncertainty.png')}<p>범위는 선수 ID를 군집으로 재표집한 1,000회 bootstrap이다. 같은 선수의 여러 시즌은 함께 재표집하고, 모든 모델의 점수는 같은 표본으로 함께 계산했다. 2026은 한 선수당 한 건이다. 이는 관측 표본에 조건부인 탐색적 범위로, 모델 재학습 불확실성·모든 시간 의존성을 해결한 확증적 구간은 아니다.</p><h3>M1–M3 직접 비교를 포함한 짝지은 차이</h3>{paired_table}<p>2026 조건부 M3 AUC는 .782이고 개별 범위는 약 .668–.893으로 넓다. 그러나 M3−M1 직접 차이의 짝지은 범위는 약 +.009–+.181이다. 개별 AUC 범위의 겹침만으로 모델 차이가 없다고 판단할 수 없다. 반면 M3−M2 범위는 0을 포함한다. 관측된 우위의 상당 부분은 <strong>현재 수준</strong> 추가에서 나타나며, 변화 자체의 큰 독립 효과로 해석하지 않는다.</p><h3>유지 정의 민감도: 36개 조합 전부 공개</h3><p>상승 .010/.020/.030 × 허용 손실 .000/.010/.020 × 다음 해 PA 100/200/300/400. 기본 정의는 바꾸지 않으며 가장 좋은 셀을 골라 결론을 만들지 않는다.</p>{sens_html}<p>M2−M1 차이는 각 기간·대상에서 36/36 정의가 양수다. M3−M2는 방향이 바뀌는 정의가 있다. <strong>36개는 서로 겹치는 기준이며 독립 검증 36회가 아니다.</strong> PA 조건을 없앤 전체 추적 진단은 “충분히 출전하고 성적도 유지”를 성공으로 묶는다. 부족한 PA는 의사결정상 실패로 포함하되 실력 하락의 증거로 부르지 않는다. 이 분석이 원래 wOBA 모델의 생존·기회 선택 편향을 완전히 제거하지는 않는다.</p><details><summary>각 정의의 AUC·분모·선수 수 전체 보기</summary>{table(full)}</details><p class="note">Hanley & McNeil (1982), Radiology 143:29–36, DOI 10.1148/radiology.143.1.7063747은 AUC 표본 변동성의 원 논문이다. 같은 사례에서 나온 AUC의 짝지은 비교는 Hanley & McNeil (1983), DOI 10.1148/radiology.148.3.6878708에서 별도로 다룬다. 여기서는 그 근사식을 적용했다고 주장하지 않고 선수 군집 bootstrap을 사용했다.</p></section>'''
    template=section_replace(template,r'<section><div class="eyebrow">04.*?</section>',sec)
    base=current.loc[current.discovery_pool & current.delta_woba.lt(.020)]
    reference=base.sort_values(['p_M1_results','player_id'],ascending=[False,True]).head(5)
    refs=reference[['display_name','woba','xwoba','projected_woba_2027']].copy()
    for col in ['woba','xwoba','projected_woba_2027']:refs[col]=refs[col].map(number)
    refs=refs.rename(columns={'display_name':'선수','woba':'2026 wOBA','xwoba':'2026 xwOBA','projected_woba_2027':'2027 M1 전망'})
    q=queue[['queue_order','display_name','woba','xwoba','delta_woba','delta_xwoba','projected_woba_2027','hypothesis']].copy()
    for col in ['woba','xwoba','projected_woba_2027']:q[col]=q[col].map(number)
    for col in ['delta_woba','delta_xwoba']:q[col]=q[col].map(lambda x:f'{x:+.3f}')
    q=q.rename(columns={'queue_order':'표시 순서','display_name':'선수','delta_woba':'wOBA 변화','delta_xwoba':'xwOBA 변화','projected_woba_2027':'2027 M1 전망','hypothesis':'확인할 가설'})
    groups=old.loc[old.delta_woba.ge(.020),['display_name','prior_pa','delta_woba','delta_xwoba','woba']].copy()
    for col in ['delta_woba','delta_xwoba']:groups[col]=groups[col].map(lambda x:f'{x:+.3f}')
    group_html=table(groups.rename(columns={'display_name':'선수','prior_pa':'2025 PA','delta_woba':'wOBA 변화','delta_xwoba':'xwOBA 변화','woba':'2026 wOBA'}))
    queue_body=f'''<section id="queue"><div class="eyebrow">05 · REVISED DECISION LISTS</div><h2>기준 전망과 미검증 신호 가설을 구분한다</h2><p>기존 discovery proxy는 wOBA ≤리그 PA 가중 평균+.020, HR ≤25, 직전 2년 중 200PA·wOBA .360 이상 시즌 없음이었다. 인지도·실제 가격을 측정한 저평가 기준은 아니다. 여기에 <strong>전년 대비 실제 wOBA 상승 &lt;.020</strong>을 추가해 이미 드러난 breakout과 덜 드러난 변화 가설을 나눴다. 이번 수정은 결과를 이미 본 뒤의 수정이며 탐색적이다.</p><h3>M1 우선: 통계적 비교 기준 5명</h3>{table(refs)}<p>같은 기준으로 과거 비교한 M1-only가 신호 screen보다 성장 yield가 높았다. 이것도 2027 독립 증거는 아니다. 유명 선수·큰 계약이 포함될 수 있으므로 이 목록이 저예산 영입 추천을 뜻하지 않는다. 계약 가격과 영입 가능성 확인은 별도 관문이다.</p><h3>별도 실험 목록: 덜 드러난 변화 가설 5명</h3>{table(q)}<p>현재 xwOBA ≥.320, 변화 ≥.010, EV +.5mph / barrel +1pp / chase −1pp / whiff −1pp 중 2개 이상이라는 기존 신호 규칙을 유지했다. 표시 순서는 M1 전망 순이지만 <strong>이 순서가 단순·무작위 기준보다 우수하다고 추천하지 않는다.</strong> 원래 13명 조사 목록은 성장 성공에서 우월하지 않았고, 새 5명 규칙도 마찬가지였다. 신호 가설은 M1 기준 검토를 대체하지 않는다.</p>{picture('signal_divergence.png')}<details><summary>이미 성적이 오른 별도 유지 관찰 그룹 8명</summary>{group_html}<p>Kyle Karros는 실제 wOBA +.068로 이미 상승이 드러난 사례다. 156PA 직전 표본도 작다. 성장 가설의 주 목록에서 제외하고 유지 관찰 사례로 옮겼다. 이 그룹을 “숨은 저평가 선수”로 부르지 않는다.</p></details></section>'''
    template=section_replace(template,r'<section id="queue">.*?</section>',queue_body)
    cards=[]
    for r in queue.itertuples():
        cards.append(f'''<article class="card"><div class="eyebrow">EXPERIMENTAL HYPOTHESIS {r.queue_order} · 우선순위 우월성 미입증</div><h3>{html.escape(r.display_name)}</h3><p class="meta">현재 소속 {html.escape(r.current_team)} · 7월 나이 {r.age:.1f} · 2026 {r.pa}PA / 직전 {r.prior_pa:.0f}PA</p><div class="mini"><span>wOBA <b>{r.prior_woba:.3f} → {r.woba:.3f}</b></span><span>xwOBA <b>{r.prior_xwoba:.3f} → {r.xwoba:.3f}</b></span></div><p><strong>가설:</strong> {html.escape(r.hypothesis)}</p><p><strong>근거:</strong> {html.escape(r.supporting_evidence)}</p><p class="opposition"><strong>반대 근거:</strong> {html.escape(r.opposing_evidence)}</p><p>EV {r.delta_exit_velocity:+.1f}mph · barrel {r.delta_barrel_pct:+.1f}pp · chase {r.delta_chase_pct:+.1f}pp · whiff {r.delta_whiff_pct:+.1f}pp</p><p>2027 M1 전망 <strong>{r.projected_woba_2027:.3f}</strong>, 현재 대비 {r.projected_delta:+.3f} · 과거 오차 범위 {r.exploratory_80pct_low:.3f}–{r.exploratory_80pct_high:.3f}</p><p><strong>영상 확인 과제:</strong> {html.escape(r.next_action)}</p><p class="meta">미확인: 2027 급여·옵션·영입 보상·역할·건강. 성공 확률이나 가치 할인 추정이 아니다.</p></article>''')
    cards_body='<section id="cards"><div class="eyebrow">06 · EVIDENCE & OPPOSITION</div><h2>다섯 가설의 근거와 확인 과제</h2><p>변화 지표는 성장을 보장하지 않는다. 아래 오차 범위는 과거 연도별 잔차의 10–90 백분위이며 미래 보장 80% 구간이 아니다. 다음 시즌 충분한 MLB 출장 기회를 얻는 조건의 전망이다.</p>'+''.join(cards)+'</section>'
    template=section_replace(template,r'<section id="cards">.*?</section>',cards_body)
    summ=summary.copy();summ['정책']=summ.policy.map({'original_13':'기존 최대13명','revised_hidden_5':'새 최대5명'})
    labels={'signal_then_M1':'신호 screen→M1','signal_then_delta_xwoba':'같은 screen→xwOBA 변화','M1_only':'M1 단독','current_woba':'현재 wOBA','current_xwoba':'현재 xwOBA','delta_xwoba':'xwOBA 변화','random_expected':'무작위 기대값'}
    summ['방법']=summ.method.map(labels)
    for c in ['growth_successes','usable_successes','available_n']:summ[c]=summ[c].map(lambda x:f'{x:.1f}' if not float(x).is_integer() else f'{int(x)}')
    pooled_html=table(summ[['정책','방법','total_slots','growth_successes','usable_successes','available_n']].rename(columns={'total_slots':'총 조사 슬롯','growth_successes':'성장 성공','usable_successes':'유용 타자 성공','available_n':'200PA 확보'}))
    yearly=backtest[['year','policy','method','base_pool_n','screen_pool_n','selected_n','growth_successes','usable_successes','available_n','random_growth_low','random_growth_high']].copy().round(2)
    yearly['method']=yearly.method.map(labels)
    ch=churn.loc[churn.k.eq(15)].pivot(index='period',columns='comparison',values='replacements').reset_index()
    ch=ch.rename(columns={'period':'목표 연도','M2_levels vs M1_results':'M1→M2 교체','M3_changes vs M2_levels':'M2→M3 교체','M3_changes vs M1_results':'M1→M3 교체'})
    protocol=(ROOT/'docs/PROSPECTIVE_2027_PROTOCOL.md').read_text()
    decision=f'''<section id="decision"><div class="eyebrow">07 · TEST THE ACTUAL SELECTION POLICY</div><h2>같은 예산으로 누구를 고르는가?</h2><p>각 목표 연도 2022–2026에서 그때의 입력만으로 screen과 순위를 적용했다. 기존 방식은 최대13명, 새 방식은 최대5명이며 screen 통과자가 적으면 k를 줄인다. <strong>같은 연도·정책의 모든 비교 방법은 동일 k와 동일 기본 후보 pool</strong>을 사용한다. 기존 방식은 총53슬롯, 새 방식은 총22슬롯이었다. 재선택된 같은 선수의 다른 시즌은 서로 다른 슬롯이며 독립 53명·22명을 뜻하지 않는다.</p><p>성장 성공 = 다음 해 200PA 이상이면서 wOBA +.020 이상. 유용 타자 = 200PA 이상·wOBA .330 이상. 출장 부족·탈락도 모든 선택 분모에 포함한다. screen→M1와 screen→xwOBA 변화 비교는 같은 통과 후보의 <strong>정렬 효과</strong>, M1 단독 등과의 비교는 screen까지 포함한 <strong>정책 전체 효과</strong>를 확인한다.</p>{pooled_html}<p><strong>기존 신호 규칙은 성장 성공 7/53건으로 무작위 기대 11.2건보다 낮았다. 새 규칙도 2/22건으로 무작위 기대 5.2건보다 낮았다.</strong> 유용 타자 성공에서는 각각 12/53, 6/22로 무작위 기대보다 높았지만 M1 단독 19/53, 9/22보다 낮았다. 따라서 성장 성공과 괜찮은 타격 수준을 혼동하지 않으며, screen을 우선 정책으로 채택하지 않는다. 같은 screen 내 정렬을 바꾸면 성장 성공 수가 바뀌지만 사후에 가장 좋은 정렬로 갈아타지 않는다.</p><p>무작위 기준은 동일 기본 pool에서 k명을 비복원 선택하는 정확한 기대값이다. 연도별 hypergeometric 95% 선택 범위를 CSV와 아래 상세 표에 공개했다. 이 범위는 무작위 선택의 분포이며 통계적 효과의 신뢰구간이 아니다. 5개 관측 시즌·반복 선수·사후 정의 수정 때문에 이 결과를 확증적 정책 우월성으로 부르지 않는다.</p><details><summary>정책별·연도별 분모와 성공 수 전체 보기</summary>{table(yearly)}</details><h3>작은 예측 오차 차이는 몇 명의 선택을 바꾸는가?</h3>{table(ch)}<p>같은 discovery pool의 Top15를 비교했다. 2026 M2→M3는 RMSE가 약 .00008 악화되면서 3명이 교체됐다. 2027 고정 전망에서 M2→M3는 2명, M1→M2와 M1→M3는 각 5명이 교체됐다. 오차의 작은 평균 차이도 경계에 있는 선수 목록을 바꿀 수 있지만, <strong>교체 자체가 성과 개선이나 경제적 이익은 아니다.</strong> Top5 결과, 평균 순위 변화와 추가·제외 이름도 CSV에 공개했다.</p><h3>2027 검증 규칙을 지금 고정한다</h3><p>2027 전체 정규시즌 종료 후, 고정된 <strong>298명 전체</strong>의 실제 PA·wOBA를 평가한다. 주 분석 RMSE·MAE, 보조 유지 정의 .020/.010/200, 36개 민감도, PA 부족을 포함한 전체 추적, 각 모델의 짝지은 AUC 차이, 동일 예산 정책 비교를 모두 보고한다. 모델·후보·기준을 2027 결과에 맞춰 바꾸지 않는다. 변경 시 별도 탐색적 버전을 남긴다.</p><p>원래 전망 고정시각과 이번 평가 계획 고정시각은 다르다. 현재 관측한 2026을 독립 검증으로 소급해서 부르지 않는다. 실제 2027 결과는 모두 pending이다.</p><details><summary>고정된 2027 평가 계획 전문</summary><pre style="white-space:pre-wrap;font-size:12px">{html.escape(protocol)}</pre></details><p class="note">계획 SHA256: {lock['sha256']['docs/PROSPECTIVE_2027_PROTOCOL.md']}<br>298명 전망·정책 ID·평가 코드의 해시도 2027_evaluation_lock.json에 고정했다. 외부 등록 preregistration을 했다는 주장은 아니다.</p><h3>의사결정과 Moneyball 범위</h3><ol><li>M1 같은 전통적 전망을 기준 자료로 먼저 확인한다.</li><li>변화 지표는 후보를 강제로 탈락·승격시키는 정책보다 개별 선수의 상충 신호를 조사하는 데 쓴다.</li><li>미검증 신호 목록은 별도 실험으로 기록하고, M1·단순·무작위 기준과 2027 결과를 비교한다.</li><li>급여·옵션·영입 가능성·보상 비용·출장 역할·건강·수비를 확인한 뒤 경제적 판단으로 옮긴다. 이 문서에는 일관된 2027 가격 자료가 없어 저평가 가격이나 ROI를 계산하지 않는다.</li></ol></section>'''
    template=section_replace(template,r'<section id="decision">.*?</section>',decision)
    template=re.sub(r'<footer>.*?</footer>',f'<footer>Juhan Youn · {TITLE} · 2026 → 2027</footer>',template,flags=re.S)
    template=template.replace('Before the Box Score',TITLE).replace('13명 조사 목록','전망·실험 목록').replace('최종 2026 검증','관측된 2026 평가').replace('final-2026','observed-2026')
    template=template.replace('AI-assisted research','').replace('AI-assisted analysis.','')
    template=template.replace('DOI 10.1148/radiology.143.1.7063747','<a href="https://pubmed.ncbi.nlm.nih.gov/7063747/">DOI 10.1148/radiology.143.1.7063747</a>').replace('DOI 10.1148/radiology.148.3.6878708','<a href="https://pubmed.ncbi.nlm.nih.gov/6878708/">DOI 10.1148/radiology.148.3.6878708</a>')
    # Existing limitations sentence referred to the old queue; point at new tests.
    template=template.replace('13명 신호 규칙도 평가 후 추가한 조사 도구다.','기존13명·새5명 신호 규칙과 추가 민감도·정책 비교는 탐색적이며 2027까지 독립 검증이 없다.')
    path=OUT/'Signals_for_Next_Season_2027_Report.html';path.write_text(template,encoding='utf-8')
    body=re.search(r'<main>(.*?)</main>',template,re.S).group(1)
    return template,style,body

def brief(queue,paired,lock):
    text=f'''# Signals for Next Season — 2027 타자 조사 리포트

Juhan Youn · 2026 전체 정규시즌 사용 · 개정본

## 검증한 범위

연간 지표로 다음 시즌 타격 수준과 이미 급상승한 성적의 유지 여부를 평가한다. 조기 발견을 검증하는 제목은 사용하지 않는다. 2022–2026은 이미 관측한 탐색적 평가이고, 2026은 모델 선택에도 사용해 독립 검증이 아니다. 원래 전망은 보존했다. 2027 평가 계획·298명 전망·후보 ID·평가 코드의 해시를 {lock['locked_at_utc']}에 고정했다.

## 결론

현재 타격 질은 전통적 성적 모델보다 유지 구분에서 높은 AUC를 보였다. 하지만 전년 대비 변화가 그 위에 더하는 효과는 작고 불안정했다. 선수 선택 정책은 별도 검증이 필요했다.

그 검증에서 기존 신호 screen→M1 정책의 성장 성공은 7/53, M1 단독은 13/53, 무작위 기대는 11.2였다. 이미 오른 선수를 제외한 새 정책은 2/22, M1 단독 7/22, 무작위 기대 5.2였다. 따라서 신호 목록을 더 효율적인 우선 조사 순위로 채택하지 않는다. M1 전망을 기준 자료로 쓰고, 변화는 개별 가설의 진단에 사용한다.

성장 성공은 다음 해 200PA 이상·실제 wOBA +.020 이상이다. 괜찮은 타자 수준을 뜻하는 200PA·wOBA .330 기준도 별도로 공개했다. 출전 부족도 모든 선택 분모에 포함한다.

## 유지 정의와 불확실성

- 기본 정의: 실제 wOBA +.020 상승, 다음 해 손실 .010 이내, 다음 해 200PA 이상.
- 상승 .010/.020/.030 × 허용 손실 .000/.010/.020 × PA 100/200/300/400의 36개 조합을 모두 공개했다. 가장 좋은 정의로 갈아타지 않는다.
- 개발 250건은 206명. 전체 breakout 추적 292건 중 42건이 다음 해 200PA 미만이었다. 2026은 86명 중 66명만 조건을 충족했다.
- 선수 군집 1,000회 재표집. 2026 M3 AUC .782, 개별 탐색적 범위 .668–.893. 같은 표본의 M3−M1 차이는 .096, 짝지은 범위 .009–.181. M3−M2 범위는 0을 포함한다. 개별 AUC 범위가 겹치는지만 보고 짝지은 차이를 판단하지 않는다.
- PA 부족을 실패로 포함하는 전체 추적 진단도 추가했다. 이것이 출장량을 모델링하거나 조건부 wOBA의 선택 편향을 완전히 해결한 것은 아니다.

## 작은 오차 차이가 바꾸는 목록

동일 discovery pool Top15 기준, 2027 전망의 M2→M3에서 2명, M1→M2와 M1→M3에서 각 5명이 교체됐다. 실제 선택이 바뀌어도 경제적 이익·성장 성공 개선은 별도 문제다.

## 미검증 성장 가설 5명

실제 wOBA 상승이 .020 미만인 후보만 별도 분류했다. xwOBA ≥.320, 변화 +.010 이상, EV +.5mph / barrel +1pp / chase −1pp / whiff −1pp 중 2개 이상 규칙을 유지했다. 아래는 M1 전망 순의 표시이며 최적 스카우팅 순위라는 주장은 아니다.

|선수|2026 wOBA|2026 xwOBA|xwOBA 변화|2027 M1 전망|확인 가설|
|---|---:|---:|---:|---:|---|
'''
    for r in queue.itertuples():text+=f'|{r.display_name}|{r.woba:.3f}|{r.xwoba:.3f}|{r.delta_xwoba:+.3f}|{r.projected_woba_2027:.3f}|{r.hypothesis}|\n'
    text+='''
Kyle Karros를 포함해 실제 성적이 이미 .020 이상 오른 8명은 별도 유지 관찰 그룹으로 옮겼다. 생산·성장 정의는 낮은 인지도나 시장 저평가를 측정하지 않는다.

## 2027 평가 계획

주 분석은 고정 모델의 다음 시즌 wOBA RMSE·MAE. 유지 분류는 보조 질문으로 남겨 같은 정의·36개 민감도·전체 추적을 평가한다. M1과 신호 정책은 같은 후보 pool·동일 조사 예산으로 비교한다. 모든 298명과 선택 목록을 보존했으며 미래 결과 칸은 pending이다. 결과를 본 뒤 모델·대상·기준을 바꾸면 별도 탐색적 버전으로 표시한다.

비용 자료가 일관되게 확보되지 않아 2027 가격 할인이나 영입 ROI는 계산하지 않았다. 수비·건강·출장 기회·영입 보상 확인이 추가로 필요하다. 공식 원본 41개, 분석 코드, 민감도 CSV, 미래 평가 CLI, 고정 평가 계획과 실행된 노트북을 패키지에 포함했다.
'''
    (OUT/'2027_Decision_Brief_KO.md').write_text(text,encoding='utf-8')

def readme(lock):
    text=f'''# Signals for Next Season

**Which underlying signals should inform next-season hitter assessment and scouting?**

Juhan Youn · Full 2026 regular season → 2027 hitter study · revised 2026-10-02.

## Conclusions

Current skill levels improved observed breakout-retention discrimination over traditional results. Year-to-year changes added small, inconsistent gains beyond levels. Annual data do not test early within-season detection. Retention remains the secondary question; it was not promoted after observing stronger results.

The actual signal-screen selection policy did not improve growth yield over simple M1-only selection: original screen→M1 7/53 versus M1-only 13/53; revised less-visible-growth screen 2/22 versus 7/22. Random expected yields were 11.2 and 5.2. Use the traditional projection as a reference, investigate change signals as hypotheses, and do not claim an optimal scouting queue or market undervaluation.

The revised report includes all 36 retention-definition sensitivity combinations, both conditional and all-followed views, unique player counts, player-cluster AUC intervals and paired M3−M1/M2−M1/M3−M2 comparisons, equal-budget policy backtests and random expected yields, and Top5/Top15 ranking churn. Observed 2022–2026 analyses are exploratory; 2026 was reused in selection. No independent validation of the selected policy has occurred.

## Read and run

- `reports/Signals_for_Next_Season_2027_Report.html`: self-contained report.
- `reports/2027_Decision_Brief_KO.md`: Korean decision brief.
- `notebooks/Signals_for_Next_Season_2027.ipynb`: executed, visible results in each code cell; Run all without internet/API keys. Embedded processed snapshot; full raw reconciliation is in the package.
- `reports/2027_scouting_queue.csv`: five experimental hypotheses, not proven priority ranks.
- `reports/2027_original_screen_groups.csv`: original 13 names split into hypotheses/already-apparent breakouts.
- `reports/retention_sensitivity.csv`, `auc_intervals.csv`, `paired_auc_intervals.csv`: all diagnostics.
- `reports/scouting_policy_backtest.csv`, `scouting_policy_names.csv`, `scouting_policy_summary.csv`: same-budget decisions and outcomes including lost playing time.
- `reports/ranking_churn.csv`, `ranking_changes_names.csv`: replacements and rank movements.
- `docs/PROSPECTIVE_2027_PROTOCOL.md`, `reports/2027_evaluation_lock.json`, `2027_frozen_evaluation.csv`: dated 2027 commitment, SHA256 hashes, all 298 frozen predictions and exact selection IDs; outcomes pending.

Install `requirements.txt`. Recreate models from cached official raw inputs with `python -m src.study`; publish diagnostics with `python -m src.revision`. Preserve the first frozen archive. A modified frozen input/code is rejected rather than silently re-frozen. Re-running models preserves numerical forecasts but may change creation metadata: perform exploratory rebuilds in a copy and never present them as the original freeze.

## Future evaluation

Only after the complete 2027 regular season, supply official MLB totals with columns `player_id,season,pa,woba`. Then:

```bash
python -m src.evaluate_2027 --outcomes official_2027.csv --season-complete --source 'official source description' --output evaluation_2027
```

The command validates frozen hashes, does not refit models, rejects duplicates/non-2027/incomplete values and writes to a fresh directory. Absence from a confirmed complete season means PA=0; an incomplete feed never counts as zero. Report all fixed comparisons, not only favorable ones. Lock date: {lock['locked_at_utc']}. This project protocol is not an externally registered preregistration.

## Design and limits

Raw official Savant 2015–2026 inputs. Predictor PA≥200, prior PA≥100. Conditional next-season outcome PA≥200. B0 current wOBA; M1 current/prior wOBA, age/age², current/prior PA, K%, BB%, ISO; M2 adds current xwOBA/barrel/hard-hit/EV/chase/whiff; M3 adds their changes. Ridge alpha=10, training-only preprocessing, strict expanding target-year folds. 2020 predictor/target excluded, with disclosed short-2020 prior baseline for 2021 and without-2022 sensitivity.

The development retention set has 250 player-year records from 206 players; resampling clusters repeated records by player and preserves paired model scores. Few years and contemporary revised historical Statcast limit inference. All-followed PA-plus-retention labels reveal unavailable players without fixing all opportunity-selection bias. No causal behavior-change effect, current-media attention, calibrated growth probability, complete roster value or acquisition ROI is established.

Official source URL/time/SHA256 metadata accompany 41 raw responses. 2026 Savant total PA reconciles to MLB (183,849), with eight unresolved individual ±1PA differences; none changes eligibility. Current affiliation is context, not a historical predictor. xwOBA uses the expected leaderboard for low-PA rounding differences. Contract costs are not comprehensively available. See the report's original sources and Hanley/McNeil 1982 and 1983 primary references for AUC uncertainty context; this implementation uses cluster bootstrap, not their parametric approximation.
'''
    (ROOT/'README.md').write_text(text,encoding='utf-8')

def run():
    from . import deliver
    print('1/5 Recompute the fixed exploratory diagnostics',flush=True)
    predictions=pd.read_csv(OUT/'historical_predictions.csv');current=pd.read_csv(OUT/'2027_all_forecasts.csv');watch=pd.read_csv(OUT/'2027_watchlist.csv')
    queue,old=prepare_queue(current)
    sensitivity=rob.sensitivity(predictions);auc,paired=rob.auc_uncertainty(predictions);backtest,names=rob.policy_backtest(predictions);summary=rob.policy_summary(backtest);churn,churn_names=rob.ranking_churn(predictions,current)
    outputs={'retention_sensitivity.csv':sensitivity,'auc_intervals.csv':auc,'paired_auc_intervals.csv':paired,'scouting_policy_backtest.csv':backtest,'scouting_policy_names.csv':names,'scouting_policy_summary.csv':summary,'ranking_churn.csv':churn,'ranking_changes_names.csv':churn_names,'sensitivity_summary.csv':rob.sensitivity_summary(sensitivity)}
    for name,d in outputs.items():d.to_csv(OUT/name,index=False)
    print('2/5 Freeze the future evaluation and render the revised report',flush=True)
    lock=freeze(current);figures(auc,current,queue)
    rendered,style,body=report(current,queue,old,auc,paired,sensitivity,summary,churn,backtest,lock)
    brief(queue,paired,lock);readme(lock)
    manifest=json.loads((OUT/'manifest.json').read_text());manifest['project']=TITLE;manifest['revised_at_utc']=lock['locked_at_utc'];manifest['revised_policy']='M1 reference; screen is a failed-growth-yield experimental hypothesis list'
    manifest['research_screen']='Exploratory signal screen plus observed wOBA rise <.020; 5 hypotheses, 8 already-apparent monitoring cases'
    manifest['code_sha256']=hashlib.sha256((ROOT/'src/study.py').read_bytes()).hexdigest();manifest['protocol_sha256']=hashlib.sha256((ROOT/'docs/PROTOCOL.md').read_bytes()).hexdigest()
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
    print('3/5 Execute all notebook cells and verify the reproduced numbers',flush=True)
    nb_check=deliver.notebook(rendered,style,body,manifest)
    print('4/5 Check frozen files, definitions, raw hashes and future evaluator',flush=True)
    freeze(current)
    assert len(queue)==5 and 'Kyle Karros' not in queue.display_name.tolist()
    assert len(sensitivity)==432
    assert (paired.valid_resamples==1000).all()
    assert rendered.count('class="card"')==5
    assert re.search(r'AI[ -]assisted',rendered,re.I) is None
    from .evaluate_2027 import evaluate_frame,load_outcomes
    # Reuse real historical outcomes to exercise the evaluation functions, not invented future results.
    historical=predictions.loc[predictions.target_season.eq(2026)].copy()
    recorded=historical[['player_id','target_pa','target_woba']].rename(columns={'target_pa':'pa','target_woba':'woba'})
    tested=evaluate_frame(historical,recorded)
    original=pd.read_csv(OUT/'model_metrics.csv').query("scope=='final_2026'")
    assert np.allclose(tested['prospective_metrics.csv'].rmse,original.rmse,atol=1e-10,rtol=0)
    for p in (ROOT/'data/raw').glob('*.meta.json'):
        m=json.loads(p.read_text());files=[x for x in p.parent.glob(p.name.removesuffix('.meta.json')+'.*') if not x.name.endswith('.meta.json')]
        assert len(files)==1 and hashlib.sha256(files[0].read_bytes()).hexdigest()==m['sha256']
    check={**nb_check,'raw_hashes_verified':41,'sensitivity_rows':432,'cluster_resamples':1000,'repeated_players_disclosed':True,'revised_hypotheses':5,'already_visible_group':8,'future_evaluator_matches_real_2026_test':True,'future_outcomes':'pending','locked_forecast_n':298,'ai_notice_removed':True,'2026_independent_validation_claim':False}
    (OUT/'validation.json').write_text(json.dumps(check,ensure_ascii=False,indent=2))
    # Remove stale generated report/notebook titles from this version of the package.
    old_report=OUT/'Before_the_Box_Score_2027_Report.html'
    if old_report.exists():old_report.unlink()
    old_nb=ROOT/'notebooks/Before_the_Box_Score_2027.ipynb'
    if old_nb.exists():old_nb.unlink()
    package=ROOT.parent.parent/'Signals_for_Next_Season_2027_Complete.zip'
    with zipfile.ZipFile(package,'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(ROOT.rglob('*')):
            if p.is_file() and '__pycache__' not in p.parts and 'notebook_validation' not in p.parts:z.write(p,'Signals_for_Next_Season_2027/'+str(p.relative_to(ROOT)))
    with zipfile.ZipFile(package) as z:assert z.testzip() is None
    print('5/5 Revised files complete:',package,flush=True)

if __name__=='__main__':run()
