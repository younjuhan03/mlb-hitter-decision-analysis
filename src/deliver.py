"""Standalone executed workbook for the revised annual scouting study."""
from pathlib import Path
import base64,gzip,hashlib,html,inspect,io,json,os,textwrap,zipfile
import numpy as np
import pandas as pd
from . import study
ROOT=study.ROOT
OUT=ROOT/'reports'
NOTES={'Heriberto Hernández': ('먼저 영상 검토', '성적 하락 속 타구 질 개선', 'wOBA는 .341→.329로 하락했지만 xwOBA는 .331→.347. EV·barrel 개선과 whiff 감소가 함께 나타났다.', 'Chase는 +2.4pp 악화했고 whiff 수준도 32.5%로 높다. M1 전망은 .329로 큰 성장을 예상하지 않는다.', '강한 타구의 구종·코스 분포를 확인하고, 유인구 대응 악화가 특정 상황에 집중되는지 영상으로 확인한다.'), 'Lawrence Butler': ('먼저 영상 검토', '타구 파워보다 컨택·선구 개선', 'Chase -1.5pp, whiff -6.2pp와 xwOBA +.021. 겉으로 드러난 wOBA 상승은 +.009에 그쳤다.', 'EV -0.8mph, barrel -0.6pp. 컨택 개선이 파워 감소를 상쇄하는지 불확실하다.', '접촉 증가가 약한 타구의 증가인지, 좋은 코스에서의 스윙 선택 개선인지 구분한다.'), 'JJ Bleday': ('비교 영상 검토', '질과 선구의 동반 개선', 'xwOBA +.064, barrel +1.7pp, chase -2.1pp, whiff -3.3pp. 여러 지표가 같은 방향이다.', '전통적 성적도 이미 +.024 상승했다. EV는 -0.3mph이고 M3 전망은 M1보다 낮다.', '성장 원인을 가설로 정리하되, 결과 상승이 이미 관측된 선수임을 기록하고 좌우 상대별 일관성을 검토한다.'), 'Spencer Steer': ('먼저 영상 검토', '완만한 결과 상승 속 타구 질 개선', 'wOBA .316→.325에 비해 xwOBA .293→.342, EV +2.4mph, barrel +4.8pp.', 'Chase +1.4pp, whiff +0.3pp로 선구·컨택 지표는 개선되지 않았다. M1 전망은 .322.', '타구 질 개선이 특정 구종이나 당겨친 타구에 한정되는지 확인한다. 개선의 반복 가능성이 조사 과제다.'), 'Coby Mayo': ('비교 영상 검토', '강한 타구 증가', 'EV +4.0mph와 barrel +3.4pp, xwOBA +.049. 454PA로 관측 표본도 늘었다.', 'Chase +3.4pp. wOBA도 +.025 상승해 완전히 숨겨진 신호는 아니다.', '높은 타구 질과 존 밖 스윙의 상충을 확인하고, MLB 출장 기회와 수비 포지션 적합성을 조사한다.'), 'Lars Nootbaar': ('먼저 영상 검토', '양호한 타구 수준과 스윙 선택', 'xwOBA .343, EV 92.0mph. EV +0.7mph, chase -1.3pp, whiff -1.8pp로 비교적 일관된 방향이다.', '334PA, barrel -0.1pp. M1 .321과 M2 .334의 전망 차이는 정보집합에 대한 민감성을 보여준다.', '표본 구성·건강·출장 기회를 확인하고, 컨택과 스윙 선택 개선이 시즌 전반에 걸쳐 나타났는지 조사한다.'), 'Kyle Karros': ('표본 확인 후 검토', '이미 드러난 큰 성적 상승', 'xwOBA +.076, barrel +7.3pp, EV +1.8mph, whiff -2.7pp.', '직전 시즌은 156PA에 불과하다. wOBA +.068로 성장 자체는 이미 전통적 성적에 드러났다. 구장 보정도 없다.', '작은 2025 표본과 구장·상대 구성 영향을 우선 확인한 뒤, 2026의 급상승이 유지될지 조사한다.'), 'Casey Schmitt': ('비교 영상 검토', '배럴과 컨택의 개선', 'xwOBA .355, barrel +3.3pp, whiff -4.4pp.', 'Chase +4.9pp, 현재 36.5%. 좋아진 접촉 결과만으로 스윙 선택이 개선됐다고 할 수 없다.', '존 밖 접촉의 질과 상대 투수 대응을 확인하고, 확장된 스윙 범위가 유지 가능한지 검토한다.'), 'Nathaniel Lowe': ('역할·비용 확인 후 검토', '회복에 가까운 타격 개선', 'EV +0.6mph, barrel +1.4pp, whiff -2.7pp, xwOBA +.032.', '7월 기준 약 31세. Chase +3.3pp, M1 전망 .316은 현재 .329보다 낮다.', '젊은 성장주와 구분하여 회복·역할 후보로 조사한다. 계약·수비·출장 가치를 함께 확인한다.'), 'Tyler Stephenson': ('역할·비용 확인 후 검토', '컨택·선구 회복 신호', 'Chase -2.9pp, whiff -4.1pp. wOBA +.001보다 xwOBA +.015가 컸다.', 'Barrel -2.1pp이고 M1 전망은 .312. 타격 지표만으로 포수의 전체 가치를 평가하지 않는다.', '스윙 선택 개선과 파워 감소를 함께 확인한다. 포수 수비와 건강·출장 부담은 별도 평가한다.'), 'Drew Gilbert': ('표본 확인 후 검토', '컨택 개선의 초기 관측', 'Whiff -3.4pp, barrel +1.0pp, xwOBA +.064.', '직전 시즌 109PA. Chase +3.6pp, EV 변화 +0.2mph. 큰 증가가 작은 비교 표본에 민감하다.', '직전 시즌의 상대·출장 구성을 확인하고, 표본 확대 이후 컨택 변화가 지속되는지 영상으로 검토한다.'), 'Brady House': ('비교 영상 검토', '배럴·스윙 지표의 동반 개선', 'Barrel +5.2pp, chase -2.7pp, whiff -1.1pp, xwOBA +.049.', '현재 chase 34.2%, whiff 29.8%. wOBA +.065로 개선은 이미 관측됐고 M1 전망은 .304.', '개선 방향과 현재의 약점 수준을 함께 본다. 높은 유인구 스윙·헛스윙에 대한 개발 과제를 확인한다.'), 'Luke Raley': ('반대 신호 우선 검토', '강한 타구와 컨택 위험의 충돌', 'Barrel +5.1pp, EV +1.3mph, xwOBA .342.', 'Chase +7.4pp, whiff 40.9%, 287PA, 약 32세. M1 전망은 .294로 낮다.', '큰 타구를 이유로 높은 성장 우선순위를 부여하지 않는다. 컨택 위험과 플래툰·출장 조건부터 검토한다.')}

def notebook(report,style,body,manifest):
    import nbformat
    from . import robustness
    from IPython.core.interactiveshell import InteractiveShell
    from IPython.utils.capture import capture_output
    payload={name:(OUT/file).read_text() for name,file in {'gold_metrics':'model_metrics.csv','gold_forecasts':'2027_all_forecasts.csv','gold_queue':'2027_scouting_queue.csv','gold_watch':'2027_watchlist.csv','manifest':'manifest.json','audit':'data_audit.csv','auc_intervals':'auc_intervals.csv','paired_auc':'paired_auc_intervals.csv','sensitivity':'retention_sensitivity.csv','selection':'scouting_policy_summary.csv','churn':'ranking_churn.csv','future_cohort':'2027_frozen_evaluation.csv','brief':'2027_Decision_Brief_KO.md'}.items()}
    payload['prospective_protocol']=(ROOT/'docs/PROSPECTIVE_2027_PROTOCOL.md').read_text()
    payload['features']=(ROOT/'data/processed/features.csv').read_text()
    payload['html']=report;payload['style']=style;payload['body']=body
    payload['charts']={name:base64.b64encode((OUT/name).read_bytes()).decode() for name in ['model_comparison.png','breakout_discrimination.png','signal_divergence.png']}
    encoded=base64.b64encode(gzip.compress(json.dumps(payload,ensure_ascii=False).encode(),mtime=0)).decode()
    cells=[]
    def md(s):cells.append(nbformat.v4.new_markdown_cell(textwrap.dedent(s).strip()))
    def code(s):cells.append(nbformat.v4.new_code_cell(textwrap.dedent(s).strip()))
    md('''# Signals for Next Season — 2026 → 2027 hitter study

**Which hitters should a resource-constrained MLB team investigate for 2027?**

Analytical question: *Do underlying skill levels and annual changes improve next-season batting forecasts and breakout-retention assessment beyond traditional results?*

**실행:** Runtime → Run all / 런타임 → 모두 실행. 실행된 출력이 이미 저장돼 있어 열자마자 결과를 읽을 수 있습니다. 각 코드 셀은 `[1/8]`–`[8/8]` 진행 표시와 표·그림 또는 결과를 출력합니다. ZIP 업로드·API 키·인터넷은 필요하지 않습니다.

**결론:** 현재 skill levels는 유지 구분의 정보를 더했으나 변화의 추가 효과는 작고 불안정했습니다. 실제 신호 screen의 과거 성장 성공은 M1 단독보다 낮았습니다. M1을 기준 자료로 두고 5명 신호 목록은 우월성이 미입증된 실험적 가설로 공개합니다. 이 연간 분석은 시즌 중 발견 시점 우위를 검증하지 않습니다. 2027 실제 성과는 pending입니다.

Juhan Youn · Frozen 2026 full regular-season snapshot.
''')
    code('''print('[1/8] 시작: 분석 환경을 불러옵니다.', flush=True)
import base64,gzip,io,json,html,zipfile
from pathlib import Path
from datetime import datetime,timezone
import numpy as np
import pandas as pd
from IPython.display import display,HTML,Markdown,Image,FileLink
from sklearn.pipeline import make_pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from sklearn.metrics import roc_auc_score,balanced_accuracy_score
pd.set_option('display.max_columns',16)
print('[1/8] 완료: Run all로 표·그림·최종 보고서까지 실행합니다.', flush=True)
''')
    md('''## 1. Validated processed snapshot

공식 원본을 대조한 처리 데이터가 이 셀에 들어 있습니다. 원본 재조회·정합성 코드는 전체 ZIP에 있습니다. 여기서는 같은 입력으로 연도별 모델, 성능, 선택 규칙, 2027 전망을 다시 계산합니다. 원본 조회시각을 이번 재실행시각으로 바꾸지 않습니다.
''')
    code('SNAPSHOT_GZIP_B64 = "'+encoded+'"\n'+'''loaded=json.loads(gzip.decompress(base64.b64decode(SNAPSHOT_GZIP_B64)))
features=pd.read_csv(io.StringIO(loaded['features']))
manifest=json.loads(loaded['manifest'])
assert features.season.max()==2026
assert features.loc[features.season.eq(2026),'target_woba'].isna().all()
assert features.loc[features.season.eq(2026),'target_pa'].isna().all()
assert int(features.eligible_pair.sum())==1806
print('데이터 고정:',manifest['as_of_utc'])
print('2026 전체 정규시즌 입력. 2027 결과는 없고 298명의 전망 입력이 있습니다.')
display(pd.read_csv(io.StringIO(loaded['audit'])).tail(4))
print('[2/8] 완료: 검증된 처리 데이터를 준비했습니다.',flush=True)
''')
    cells[-1].metadata={'tags':['hide-input'],'jupyter':{'source_hidden':True},'collapsed':True}
    md('''## 2. Nested models and chronological evaluation

M1: 전통적 성적·나이·이전 기록. M2: M1 + 현재 Statcast 수준. M3: M2 + 전년 대비 변화. 각 테스트에서 학습의 목표 연도는 반드시 테스트 목표 연도보다 이전입니다. 고정 Ridge α=10, 학습 내 대치·표준화.
''')
    constants=f'TRAD={study.TRAD!r}\nSKILLS={study.SKILLS!r}\nCHANGE={study.CHANGE!r}\nMODELS={study.MODELS!r}\nDEV_YEARS={study.DEV_YEARS!r}\nALPHA={study.ALPHA!r}\n'
    definitions='\n\n'.join(inspect.getsource(f) for f in [study.fit_model,study.evaluate,study.metric_table,study.selection_rule,study.paired_gain,study.decision_backtest,study.breakout_diagnostics,study.forecast])
    constants += 'ROB_MODELS='+repr(robustness.MODELS)+'\nRISES='+repr(robustness.RISES)+'\nLOSSES='+repr(robustness.LOSSES)+'\nTARGET_PA='+repr(robustness.TARGET_PA)+'\nfrom itertools import product\nfrom scipy.stats import hypergeom,spearmanr\n'
    definitions += '\n\n'+'\n\n'.join(inspect.getsource(f).replace('MODELS','ROB_MODELS') for f in [robustness.signal_count,robustness.screen,robustness.retention_data,robustness.sensitivity,robustness.auc_uncertainty,robustness.decision_outcomes,robustness.policy_backtest,robustness.policy_summary,robustness.ranking_churn,robustness.sensitivity_summary])
    code(constants+'\n'+definitions+'''\nprint('[3/8] 완료: 학습·검증·전망 함수를 정의했습니다.',flush=True)
print('목표 시즌 순서를 지켜 평가하며, 입력에 미래 target 변수를 쓰지 않습니다.')
''')
    md('''## 3. Primary and secondary results

전체 예측의 RMSE/MAE가 주 분석입니다. 이미 오른 타자의 유지 여부 AUC는 보조 분석입니다. 작은 차이를 큰 효과라고 해석하지 않습니다.
''')
    code('''print('[4/8] 실행 중: 연도별 미래 예측을 다시 계산합니다.',flush=True)
predictions,coefficients=evaluate(features)
metrics=metric_table(predictions)
policy=selection_rule(metrics)
gold=pd.read_csv(io.StringIO(loaded['gold_metrics']))
assert np.allclose(metrics[['rmse','mae','pa_weighted_rmse']],gold[['rmse','mae','pa_weighted_rmse']],atol=1e-10,rtol=0)
assert policy['selected_model']=='M1_results'
diagnostics=breakout_diagnostics(predictions)
display(metrics.loc[metrics.scope.isin(['development','final_2026'])].round(5))
display(diagnostics.round(3))
display(Image(data=base64.b64decode(loaded['charts']['model_comparison.png'])))
print('현재 Skill levels는 유지 여부 구분의 단서. 변화의 추가 효과는 작고 일관적이지 않습니다.')
print('보수적 공식 모델:',policy['selected_model'])
print('[4/8] 완료: 저장된 기준 결과와 수치가 일치합니다.',flush=True)
''')
    md('''## 4. Decision backtest and uncertainty

모든 선택을 분모에 포함합니다. 성장 성공 = 다음 해 200PA 이상·wOBA +.020 이상. 유용 타자 성공 = 200PA 이상·wOBA .330 이상. 신호 조사 정책을 동일 pool·동일 예산의 단순·무작위 기준과 따로 비교하며, 이미 관측한 결과이므로 탐색적 평가입니다.
''')
    code('''print('[5/8] 실행 중: 민감도·군집 AUC·동일 예산 정책을 다시 계산합니다.',flush=True)
backtest,backtest_names=decision_backtest(predictions)
gains=[paired_gain(predictions,'M1_results','M2_levels'),paired_gain(predictions,'M2_levels','M3_changes')]
sens=sensitivity(predictions)
auc_ci,paired_ci=auc_uncertainty(predictions)
policy_bt,policy_names=policy_backtest(predictions)
policy_sum=policy_summary(policy_bt)
gold_current_for_ranks=pd.read_csv(io.StringIO(loaded['gold_forecasts']))
churn,churn_names=ranking_churn(predictions,gold_current_for_ranks)
for calculated,key,columns in [(sens,'sensitivity',['auc']),(auc_ci,'auc_intervals',['auc','low','high']),(paired_ci,'paired_auc',['auc_gain','low','high']),(policy_sum,'selection',['growth_successes','usable_successes'])]:
    gold_table=pd.read_csv(io.StringIO(loaded[key]))
    assert np.allclose(calculated[columns],gold_table[columns],atol=1e-10,rtol=0,equal_nan=True)
display(auc_ci.round(3))
display(paired_ci.round(3))
display(sensitivity_summary(sens).round(3))
display(policy_sum.round(2))
display(churn.loc[churn.k.eq(15),['period','comparison','replacements']])
print('신호 screen의 성장 성공은 단순 M1보다 낮았습니다. 우월한 조사 순위로 채택하지 않습니다.')
print('모든 정책은 같은 pool·같은 k. 출전 부족도 실패로 포함합니다. 범위는 선수 군집 탐색적 범위입니다.')
print('[5/8] 완료: 모든 추가 진단이 저장된 결과와 일치합니다.',flush=True)
''')
    md('''## 5. Frozen 2027 forecasts and exploratory research queue

2027 결과는 학습·검증·후보 선택 어디에도 없습니다. 전망은 다음 시즌 충분한 MLB 타석을 얻는 조건입니다. 오차 범위는 과거 잔차 범위이며 미래 보장 구간이 아닙니다.
''')
    code('''print('[6/8] 실행 중: 완료된 2026까지 학습해 2027을 전망합니다.',flush=True)
current,watch,bands=forecast(features,predictions,policy)
gold_current=pd.read_csv(io.StringIO(loaded['gold_forecasts'])).set_index('player_id')
for name in MODELS:
    assert np.allclose(current.set_index('player_id')['p_'+name],gold_current['p_'+name],atol=1e-10,rtol=0)
gold_watch=pd.read_csv(io.StringIO(loaded['gold_watch']))
assert watch.player_id.tolist()==gold_watch.player_id.tolist()
# Preserve original creation time for an unchanged snapshot replay.
current['created_at_utc']=current.player_id.map(gold_current.created_at_utc)
watch['created_at_utc']=watch.player_id.map(gold_current.created_at_utc)
queue=current.loc[screen(current,hidden=True)].sort_values(['projected_woba_2027','player_id'],ascending=[False,True]).copy()
gold_queue=pd.read_csv(io.StringIO(loaded['gold_queue']))
assert queue.player_id.tolist()==gold_queue.player_id.tolist()
queue=gold_queue.copy()
display(queue[['queue_order','display_name','pa','woba','xwoba','delta_xwoba','projected_woba_2027','review_priority']].round(3))
print('5명 screen은 사후 수정한 실험적 가설. M1보다 성장 성공이 낮아 우선 정책으로 채택하지 않습니다.')
display(watch[['rank','display_name','projected_woba_2027','projected_delta','bootstrap_top15_share']].round(3))
print('Top15 포함 비율은 학습 재표집에 대한 순위 안정성으로, 성공 확률이 아닙니다.')
print('[6/8] 완료: 모든 전망과 선수 순서가 고정 결과와 일치합니다.',flush=True)
''')
    md('''## 6. Read the recommendation

코드를 하나씩 해석하지 않아도 아래에 결론과 주요 조사 근거가 표시됩니다. 2027 비용은 확인되지 않아 Moneyball ROI를 계산하지 않았습니다.
''')
    code('''display(Markdown(loaded['brief']))
display(Image(data=base64.b64decode(loaded['charts']['signal_divergence.png'])))
print('[7/8] 완료: 한국어 결론·조사 목록을 표시했습니다.',flush=True)
''')
    md('''## 7. Final report and result files

전체 HTML 보고서를 아래에 표시하며 현재 실행 폴더에 저장합니다. 파일이 내려받아지지 않으면 Colab 왼쪽 파일 탭에서 ZIP을 받을 수 있습니다. 미래 결과 칸은 pending으로 남깁니다.
''')
    code('''result_dir=Path('before_the_box_score_2027_results');result_dir.mkdir(exist_ok=True)
for name,frame in {'model_metrics.csv':metrics,'breakout_diagnostics.csv':diagnostics,'decision_backtest.csv':backtest,'historical_predictions.csv':predictions,'2027_all_forecasts.csv':current,'2027_projection_top15.csv':watch,'2027_scouting_queue.csv':queue,'retention_sensitivity.csv':sens,'auc_intervals.csv':auc_ci,'paired_auc_intervals.csv':paired_ci,'scouting_policy_backtest.csv':policy_bt,'scouting_policy_names.csv':policy_names,'scouting_policy_summary.csv':policy_sum,'ranking_churn.csv':churn,'ranking_changes_names.csv':churn_names}.items():
    frame.to_csv(result_dir/name,index=False)
pending=queue[['queue_order','player_id','display_name','projected_woba_2027','created_at_utc']].copy()
pending['actual_pa_2027']=np.nan;pending['actual_woba_2027']=np.nan;pending['status']='pending'
pending.to_csv(result_dir/'2027_scouting_outcome_log.csv',index=False)
(result_dir/'2027_Decision_Brief_KO.md').write_text(loaded['brief'],encoding='utf-8')
report_path=result_dir/'Signals_for_Next_Season_2027_Report.html'
report_path.write_text(loaded['html'],encoding='utf-8')
pd.read_csv(io.StringIO(loaded['future_cohort'])).to_csv(result_dir/'2027_frozen_evaluation.csv',index=False)
(result_dir/'PROSPECTIVE_2027_PROTOCOL.md').write_text(loaded['prospective_protocol'],encoding='utf-8')
(result_dir/'snapshot_manifest.json').write_text(loaded['manifest'],encoding='utf-8')
(result_dir/'replay.json').write_text(json.dumps({'replayed_at_utc':datetime.now(timezone.utc).isoformat(),'frozen_at_utc':manifest['as_of_utc'],'gold_predictions_match':True,'future_results':'2027 pending'},indent=2),encoding='utf-8')
zip_path=Path('Signals_for_Next_Season_2027_Notebook_Results.zip')
with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED) as z:
    for path in sorted(result_dir.iterdir()):z.write(path,path.name)
print('[8/8] 전체 완료: 아래 보고서에 결과가 표시됩니다.',flush=True)
display(HTML('<style>'+loaded['style']+'</style><main>'+loaded['body']+'</main>'))
display(FileLink(str(report_path),result_html_prefix='HTML 보고서: '))
display(FileLink(str(zip_path),result_html_prefix='결과 ZIP: '))
try:
    from google.colab import files
except ImportError:
    print('보고서와 ZIP을 위 링크 또는 실행 폴더에서 열 수 있습니다.')
else:
    try:files.download(str(zip_path))
    except Exception:print('화면 결과는 완료됐습니다. Colab 왼쪽 파일 탭에서 ZIP을 받으세요.')
''')
    nb=nbformat.v4.new_notebook(cells=cells,metadata={'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},'language_info':{'name':'python','version':'3.12'},'colab':{'name':'Signals_for_Next_Season_2027.ipynb','provenance':[]}})
    shell=InteractiveShell.instance();old=Path.cwd()
    test_dir=ROOT/'notebook_validation';test_dir.mkdir(exist_ok=True)
    try:
        os.chdir(test_dir)
        for cell in nb.cells:
            if cell.cell_type!='code':continue
            with capture_output() as captured:result=shell.run_cell(cell.source,store_history=True)
            if result.error_before_exec:raise result.error_before_exec
            if result.error_in_exec:raise result.error_in_exec
            cell.execution_count=result.execution_count;cell.outputs=[]
            for name,value in [('stdout',captured.stdout),('stderr',captured.stderr)]:
                if value:cell.outputs.append(nbformat.v4.new_output('stream',name=name,text=value))
            for output in captured.outputs:cell.outputs.append(nbformat.v4.new_output('display_data',data=output.data,metadata=output.metadata))
            print('Executed notebook cell',cell.execution_count,flush=True)
    finally:os.chdir(old)
    code_cells=[c for c in nb.cells if c.cell_type=='code']
    assert len(code_cells)==8
    for number,cell in enumerate(code_cells,1):
        assert cell.execution_count==number
        assert any(o.output_type=='stream' and f'[{number}/8]' in o.text for o in cell.outputs)
        assert not any(o.output_type=='error' for o in cell.outputs)
    assert any('image/png' in o.get('data',{}) for o in code_cells[3].outputs)
    assert any('text/html' in o.get('data',{}) and '다섯 가설의 근거와 확인 과제' in o.data['text/html'] for o in code_cells[-1].outputs)
    nbformat.validate(nb)
    path=ROOT/'notebooks/Signals_for_Next_Season_2027.ipynb';nbformat.write(nb,path)
    return {'executed_code_cells':8,'all_cells_visible_progress':True,'rich_png_and_html_outputs':True,'gold_metrics_and_forecasts_match':True,'notebook_path':str(path.relative_to(ROOT))}


def run():
    from .revision import run as publish
    publish()

if __name__=='__main__':run()
