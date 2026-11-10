"""Create standalone report HTML, executive summaries and a Korean reading guide.
Run: python -m src.delivery_bundle
"""
from pathlib import Path
import io, html, re, json, base64
import fitz
import pandas as pd
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.enums import TA_LEFT

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports'
TEAL=colors.HexColor('#237e7a'); INK=colors.HexColor('#243d4b'); LIGHT=colors.HexColor('#eef5f5')
pdfmetrics.registerFont(TTFont('ReviewSans',str(ROOT/'reference/DejaVuSans.ttf')))
pdfmetrics.registerFont(TTFont('ReviewKorean',io.BytesIO(fitz.Font('korea').buffer)))

STYLE='''*{box-sizing:border-box}body{margin:0;color:#243d4b;background:#edf3f3;font:16px/1.65 system-ui,sans-serif}main{max-width:1000px;margin:32px auto;padding:30px;background:white;border-radius:12px}h1{font-size:38px;line-height:1.2}h2{font-size:22px;color:#237e7a;margin-top:28px}p{margin:12px 0}table{border-collapse:collapse;width:100%;font-size:14px;margin:18px 0}th{background:#243d4b;color:white;text-align:left}td,th{padding:10px;border-bottom:1px solid #dce6e8}tbody tr:nth-child(even){background:#f2f7f7}.meta{color:#647b87;font-size:13px}.callout{background:#e9f5f2;padding:16px;border-left:4px solid #237e7a}.note{font-size:13px;color:#536e79}pre{white-space:pre-wrap;background:#f1f5f5;padding:14px;font:14px/1.6 ui-monospace,monospace}a{color:#237e7a}@media(max-width:650px){main{margin:0;padding:20px}h1{font-size:29px}table{font-size:12px}td,th{padding:7px}}@media print{body{background:white}main{margin:0;max-width:none;padding:0}h2{break-after:avoid}tr{break-inside:avoid}}'''

SUMMARY_EN='''# Signals for Next Season

Juhan Youn | 2027 hitter assessment | Executive summary | Corrected 2026-10-04

## Question and decision

Do current underlying skills and annual changes improve next-season batting forecasts and breakout-retention assessment beyond traditional results? The practical decision is how to allocate limited hitter-review time after the season ends.

## Main finding

Current skill levels improved observed retention discrimination, but annual changes added small and inconsistent gains. The signal-screen policy produced fewer historical growth successes than M1-only selection. Retain M1 as the forecast reference and treat the five signal candidates as exploratory investigation hypotheses.

## Design and forecast error

Savant 2015-2026; expanding target-year evaluations for 2022-2026. M1 uses traditional results; M2 adds skill levels; M3 adds changes. Ridge alpha=10. Eligible input: PA >=200 and prior PA >=100. Forecast-error evaluation conditions on next-season PA >=200.

| Period | M1 RMSE | M2 RMSE | M3 RMSE |
|---|---:|---:|---:|
| 2022-2025 | .03201 | .03185 | .03168 |
| Most recent year: 2026 | .03075 | .02972 | .02980 |

M3 did not pass the adoption rule. M2's development MAE was slightly higher than M1's at the fixed alpha=10. The observed 2026 comparison informed selection and is not independent validation.

## Same-budget growth success

| Policy | Slots | Screen then M1 | M1-only | Random expected |
|---|---:|---:|---:|---:|
| Original screen | 53 | 7 | 13 | 11.20 |
| Revised screen | 22 | 2 | 7 | 5.18 |

Growth success = next-season PA >=200 and wOBA increase >=.020. Insufficient PA counts as failure. Retention AUC answers a different question from top-k growth yield. These observed comparisons are exploratory.

## Five 2027 investigation hypotheses

| Hitter | 2026 wOBA | xwOBA | xwOBA change | 2027 M1 |
|---|---:|---:|---:|---:|
| Heriberto Hernández | .329 | .347 | +.016 | .329 |
| Lawrence Butler | .319 | .326 | +.021 | .324 |
| Spencer Steer | .325 | .342 | +.049 | .322 |
| Lars Nootbaar | .320 | .343 | +.026 | .321 |
| Tyler Stephenson | .320 | .326 | +.015 | .312 |

Nootbaar's 334PA followed injury recovery and a midseason trade; health and within-season consistency require review. The display order follows M1 and does not establish an optimal scouting priority.

## Prospective check and limits

All 298 forecasts and evaluation rules are frozen; 2027 outcomes remain pending. Annual data do not test earlier within-season detection or causality. Player availability, repeated hitters, few years, and historical data revisions limit inference. No acquisition ROI or market undervaluation is estimated.
'''

SUMMARY_KO='''# Signals for Next Season

Juhan Youn | 2027 타자 평가 | 핵심 요약 | 2026-10-04 수정본

## 질문과 의사결정

전통적 성적에 현재 타격 기술 수준과 전년 대비 변화를 더하면 다음 시즌 타격 전망과 급상승 성적의 유지 여부를 더 잘 평가할 수 있는가? 시즌 종료 후 제한된 타자 조사 시간을 누구에게 배분할지 검토한다.

## 핵심 결론

현재 기술 수준은 관측된 유지 여부 구분에 정보를 더했지만, 변화의 추가 효과는 작고 불안정했다. 신호로 선수를 먼저 걸러내는 정책은 M1 단독보다 과거 성장 성공 수가 적었다. M1을 전망 기준으로 유지하고, 5명은 실험적 조사 가설로 다룬다.

## 설계와 전망 오차

Savant 2015-2026, 목표 연도 2022-2026의 시간 순서 평가. M1은 전통 성적, M2는 현재 기술 수준 추가, M3는 변화 추가. Ridge alpha=10. 입력 PA 200 이상, 직전 PA 100 이상이며, 전망 오차는 다음 시즌 PA 200 이상 조건에서 평가한다.

| 기간 | M1 RMSE | M2 RMSE | M3 RMSE |
|---|---:|---:|---:|
| 2022-2025 | .03201 | .03185 | .03168 |
| 최근 관측 연도: 2026 | .03075 | .02972 | .02980 |

M3는 채택 기준을 통과하지 못했다. 고정 alpha=10에서 M2의 개발 MAE는 M1보다 조금 높았다. 2026은 모델 선택에도 사용했으므로 독립 검증이 아니다.

## 같은 조사 예산의 성장 성공

| 정책 | 조사 슬롯 | 신호 후 M1 | M1 단독 | 무작위 기대 |
|---|---:|---:|---:|---:|
| 기존 신호 규칙 | 53 | 7 | 13 | 11.20 |
| 수정 신호 규칙 | 22 | 2 | 7 | 5.18 |

성장 성공은 다음 시즌 PA 200 이상이며 wOBA가 .020 이상 상승한 경우다. 출전 부족도 실패로 포함한다. 유지 AUC와 상위 후보의 성장 성공은 다른 질문이다. 역사 비교는 탐색적이다.

## 2027 조사 가설 5명

| 선수 | 2026 wOBA | xwOBA | xwOBA 변화 | 2027 M1 |
|---|---:|---:|---:|---:|
| Heriberto Hernández | .329 | .347 | +.016 | .329 |
| Lawrence Butler | .319 | .326 | +.021 | .324 |
| Spencer Steer | .325 | .342 | +.049 | .322 |
| Lars Nootbaar | .320 | .343 | +.026 | .321 |
| Tyler Stephenson | .320 | .326 | +.015 | .312 |

Nootbaar의 334PA는 부상 복귀와 시즌 중 트레이드를 겪은 표본이다. 건강과 시즌 내 신호의 일관성을 따로 확인해야 한다. 표시는 M1 전망 순이며 최적 조사 순위라는 뜻은 아니다.

## 향후 검증과 한계

298명 전망과 평가 규칙을 고정했으며 2027 실제 결과는 pending이다. 연간 자료로 시즌 중 조기 발견이나 인과 효과를 검증하지 않는다. 출장 기회, 반복 선수, 적은 연도와 과거 자료 수정이 한계다. 영입 ROI나 시장 저평가 가격은 추정하지 않았다.
'''

GUIDE_KO='''# Signals for Next Season - 읽기와 실행 가이드

Juhan Youn | 수정본 사용 안내 | 2026-10-04

## 1. 먼저 읽을 파일

영문 Summary는 결과를 빠르게 설명하는 1쪽 요약이다. 한국어 Summary는 같은 핵심 결론을 이해하는 데 사용한다. 전체 영문 PDF와 HTML에는 선수 카드, 민감도, 정책 비교와 부록이 들어 있다. 한국어 본문 HTML은 core 분석 설명이며 영문 추가 부록 전체의 번역본은 아니다. ZIP 안 reference의 Original PDF는 수정 전 기록이다.

## 2. 이 프로젝트를 한 문장으로 설명하기

"전통적 성적만 사용하는 모델에 현재 Statcast 기술 수준과 연간 변화를 추가해 다음 시즌 타격 전망을 비교하고, 신호로 고른 선수들이 실제로 더 자주 성장했는지 같은 예산으로 평가했습니다."

## 3. 무엇을 발견했는가

현재 기술 수준은 이미 성적이 오른 선수의 유지 여부를 구분하는 데 정보를 더했다. 변화 지표를 추가한 효과는 작고 일정하지 않았다. 좋은 신호를 가진 후보를 먼저 거르는 정책의 성장 성공은 M1 단독보다 낮았다. 따라서 공식 전망은 M1을 유지하고, 선수 5명은 개별 조사 가설로 제시한다.

## 4. 용어와 서로 다른 질문

PA는 타석 수다. wOBA는 실제 타격 결과의 가중 지표이고, xwOBA는 관측된 타구와 다른 입력으로 계산한 기대 지표다. xwOBA가 더 높다고 다음 시즌 성장을 보장하지 않는다. RMSE와 MAE는 전망 오차라 낮을수록 좋다. AUC는 성공과 실패의 순서 구분 능력이며 성공 확률이 아니다.

유지 질문: 입력 시즌 wOBA가 .020 이상 오른 선수가 다음 해 PA 200 이상을 확보하고 하락 폭을 .010 이내로 유지했는가?

성장 질문: 정책으로 고른 후보가 다음 해 PA 200 이상을 확보하고 wOBA를 추가로 .020 이상 높였는가?

유용 타자 질문: 다음 해 PA 200 이상이며 wOBA .330 이상인가? 세 질문의 성공 수를 서로 바꾸어 해석하지 않는다.

## 5. 노트북 실행

Google Colab에서 File > Upload notebook으로 .ipynb를 연다. 저장된 표와 그림을 먼저 읽고, 재실행하려면 Runtime > Run all을 누른다. 첫 실행은 임베드된 처리 자료를 사용하며 ZIP 업로드나 API 키가 필요 없다. [1/8]부터 [8/8]까지 진행 메시지가 표시된다. 표와 그림을 생성하는 셀은 작업 시간이 걸릴 수 있다.

마지막 셀은 core 한국어 HTML과 결과 ZIP을 생성한다. 이번 전체 영문 HTML, 요약본, 가이드는 별도 delivery 산출물이므로 원래 노트북의 Run all로 자동 생성되지는 않는다. 전체 ZIP의 python -m src.delivery_bundle로 이 문서 묶음을 다시 만들 수 있다.

## 6. 코드의 큰 흐름

원자료 정합성 확인 -> 선수별 연간 자료 연결 -> 현재 수준과 전년 대비 변화 생성 -> 이전에 완료된 목표 연도만 학습 -> 이후 연도 예측 -> 오차와 유지 AUC 계산 -> 같은 후보 pool과 조사 예산으로 정책 비교 -> 2027 전망 고정.

모델 전처리와 Ridge 학습은 학습 자료 안에서만 수행한다. PDF 예시의 features는 DataFrame이고 feature_cols는 사용할 열 이름 목록이다. train[feature_cols]는 학습표에서 그 열들만 꺼낸다는 뜻이다. 공식 코드의 fit_model 함수는 같은 역할을 수행한다.

## 7. 숫자를 설명할 때의 주의점

2026은 이미 관측했고 모델 선택에도 사용했으므로 독립 검증이 아니다. 2027 실제 결과는 아직 없다. 5명 목록은 입증된 최고 순위나 5명의 독립 검증이 아니다. 과거 조사 슬롯에는 같은 선수의 다른 시즌이 포함된다.

33/36은 반올림 전 AUC 차이로 센 값이다. 0.000처럼 보이는 표시 값도 실제로는 양수일 수 있다. 역사 무작위 표의 probability-ordered 양측 꼬리와 Appendix E의 상측 단측 .025 기준은 서로 다른 양이다. Nootbaar의 334PA에는 부상 복귀와 시즌 중 팀 이동의 맥락이 있다.

## 8. 제출 자료와 재현 파일

처음 보여줄 자료: 영문 Summary와 전체 Report. 코드를 검토할 자료: 노트북, src/study.py, src/robustness.py와 이번 검증 코드. 2027_scouting_queue.csv는 실험 가설 5명, 2027_watchlist.csv는 M1 전망 Top15, 2027_all_forecasts.csv는 전체 전망 자료다. 같은 목록이 아니다.

핵심 검증은 python -m src.review_verification으로 다시 계산한다. 공식 2027 전망 및 평가 lock은 바꾸지 않는다. 2027 시즌 종료 후 실제 결과를 넣는 절차는 README의 Future evaluation을 따른다. 파일을 공개할 때 질문, 데이터 처리, 시간 순서 검증, 결과와 한계를 자신의 말로 설명할 수 있어야 한다.
'''

def chunks(markdown):
    blocks=re.split(r'\n\s*\n',markdown.strip())
    for b in blocks:
        if b.startswith('|'):
            rows=[[v.strip() for v in line.strip().strip('|').split('|')] for line in b.splitlines()]
            yield 'table',[rows[0]]+rows[2:]
        elif b.startswith('# '):yield 'title',b[2:]
        elif b.startswith('## '):yield 'heading',b[3:]
        else:yield 'paragraph',b.replace('\n',' ')

def render_html(markdown,lang):
    parts=[]
    for kind,text in chunks(markdown):
        if kind=='table':
            header=''.join('<th>'+html.escape(x)+'</th>' for x in text[0])
            rows=''.join('<tr>'+''.join('<td>'+html.escape(x)+'</td>' for x in row)+'</tr>' for row in text[1:])
            parts.append('<table><thead><tr>'+header+'</tr></thead><tbody>'+rows+'</tbody></table>')
        else:
            tag={'title':'h1','heading':'h2','paragraph':'p'}[kind]
            parts.append('<'+tag+'>'+html.escape(text)+'</'+tag+'>')
    return '<!doctype html><html lang="'+lang+'"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Signals for Next Season</title><style>'+STYLE+'</style><main>'+''.join(parts)+'</main></html>'

def pdf(markdown,path,lang,guide=False):
    font='ReviewKorean' if lang=='ko' else 'ReviewSans'
    body=ParagraphStyle('Body',fontName=font,fontSize=9.2,leading=13.2,textColor=INK,spaceAfter=6 if guide else 5,wordWrap='CJK' if lang=='ko' else None)
    heading=ParagraphStyle('Heading',parent=body,fontSize=11,leading=14,textColor=TEAL,spaceBefore=9 if guide else 7,spaceAfter=5)
    title=ParagraphStyle('Title',parent=body,fontSize=24,leading=28,spaceAfter=7)
    cell=ParagraphStyle('Cell',parent=body,fontSize=8.4,leading=11,spaceAfter=0)
    story=[]
    for kind,value in chunks(markdown):
        if guide and kind=='heading' and value.startswith('5.'):
            story.append(PageBreak())
        if kind=='table':
            tabledata=[[Paragraph(html.escape(v),cell) for v in row] for row in value]
            n=len(value[0]);width=523.27
            widths=([158]+[(width-158)/(n-1)]*(n-1)) if n==5 else ([196]+[(width-196)/(n-1)]*(n-1))
            t=Table(tabledata,colWidths=widths,hAlign='LEFT',repeatRows=1)
            t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),LIGHT),('TEXTCOLOR',(0,0),(-1,-1),INK),('TOPPADDING',(0,0),(-1,-1),4.5),('BOTTOMPADDING',(0,0),(-1,-1),4.5),('LINEBELOW',(0,0),(-1,0),.8,TEAL),('LINEBELOW',(0,1),(-1,-1),.25,colors.HexColor('#dce6e8')),('VALIGN',(0,0),(-1,-1),'TOP')]))
            story += [t,Spacer(1,6)]
        elif guide and kind=='title':
            a,b=value.split(' - ',1)
            story.append(Paragraph(html.escape(a),ParagraphStyle('EnglishTitle',parent=title,fontName='ReviewSans')))
            story.append(Paragraph(html.escape(b),ParagraphStyle('GuideSubtitle',parent=heading,fontSize=15,leading=20,spaceBefore=0,spaceAfter=8)))
        else:story.append(Paragraph(html.escape(value),{'title':title,'heading':heading,'paragraph':body}[kind]))
    def footer(canvas,doc):
        canvas.setFont('ReviewSans',7.5);canvas.setFillColor(colors.HexColor('#647b87'))
        canvas.drawString(36,21,'Juhan Youn | Signals for Next Season | 2026-10-04')
        canvas.drawRightString(559.27,21,str(doc.page))
    SimpleDocTemplate(str(path),pagesize=(595.27,841.89),leftMargin=36,rightMargin=36,topMargin=30,bottomMargin=36).build(story,onFirstPage=footer,onLaterPages=footer)

def full_report_html():
    source=OUT/'Signals_for_Next_Season_2027_Report_EN_Corrected.pdf'
    doc=fitz.open(source);pages=[]
    for i,page in enumerate(doc):
        png=base64.b64encode(page.get_pixmap(matrix=fitz.Matrix(2,2)).tobytes('png')).decode()
        visual=f'<img src="data:image/png;base64,{png}" alt="Report page {i+1}" width="{int(page.rect.width*2)}" height="{int(page.rect.height*2)}" loading="lazy">'
        links=[]
        for a in page.get_links():
            if 'uri' in a:
                r=a['from'];w=page.rect.width;h=page.rect.height
                links.append(f'<a class="link" href="{html.escape(a["uri"],quote=True)}" target="_blank" rel="noopener" aria-label="Open source" style="left:{100*r.x0/w:.5f}%;top:{100*r.y0/h:.5f}%;width:{100*r.width/w:.5f}%;height:{100*r.height/h:.5f}%"></a>')
        text=page.get_text(sort=True)
        pages.append(f'<section class="page" id="page-{i+1}"><h2>Page {i+1}</h2><div class="paper">{visual}{"".join(links)}</div><pre class="reader">{html.escape(text)}</pre></section>')
    nav=''.join(f'<a href="#page-{i}">{i}</a>' for i in range(1,len(doc)+1))
    css='''body{margin:0;background:#edf3f3;color:#243d4b;font:15px/1.5 system-ui,sans-serif}header{padding:22px 25px;background:#243d4b;color:white}h1{margin:0;font-size:25px}header p{margin:7px 0;color:#d3e4e7}nav{position:sticky;top:0;background:white;z-index:3;padding:10px 20px;box-shadow:0 2px 8px #0001;display:flex;gap:10px;flex-wrap:wrap;align-items:center}nav a{color:#237e7a;padding:3px}button,input{padding:8px;border:1px solid #c6d7d9;border-radius:5px}button{cursor:pointer}main{max-width:980px;margin:20px auto}.page{margin:24px 0;scroll-margin-top:120px}.page h2{font-size:13px;color:#647b87;margin:5px 12px}.paper{position:relative;box-shadow:0 3px 18px #0001}.paper svg{display:block;width:100%;height:auto}.link{position:absolute}.reader{display:none;white-space:pre-wrap;background:white;font:15px/1.65 system-ui,sans-serif;padding:24px;margin:0}.reading .reader{display:block}.reading .paper{display:none}[hidden]{display:none!important}@media print{header,nav,.page h2{display:none}main{margin:0;max-width:none}.page{break-after:page;margin:0}.paper{box-shadow:none}}'''
    css=css.replace('.paper svg{','.paper img{')
    js='''document.getElementById('mode').onclick=()=>{document.body.classList.toggle('reading');document.getElementById('mode').textContent=document.body.classList.contains('reading')?'Document view':'Reading view'};document.getElementById('search').oninput=e=>{let n=0,q=e.target.value.toLowerCase().trim();document.querySelectorAll('.page').forEach(p=>{let hit=p.querySelector('.reader').textContent.toLowerCase().includes(q);p.hidden=!hit;if(hit)n++});document.getElementById('count').textContent=n+' pages'};'''
    output='<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Signals for Next Season - Full report</title><style>'+css+'</style><header><h1>Signals for Next Season</h1><p>Juhan Youn | Full corrected English report | 2026-10-04</p></header><nav><button id="mode">Reading view</button><input id="search" placeholder="Search report" aria-label="Search report"><span id="count">27 pages</span>'+nav+'</nav><main>'+''.join(pages)+'</main><script>'+js+'</script></html>'
    (OUT/'Signals_for_Next_Season_2027_Report_EN_Corrected.html').write_text(output)

def main():
    for lang,text in [('EN',SUMMARY_EN),('KO',SUMMARY_KO)]:
        name='Signals_for_Next_Season_2027_Summary_'+lang
        (OUT/(name+'.md')).write_text(text)
        (OUT/(name+'.html')).write_text(render_html(text,lang.lower()))
        pdf(text,OUT/(name+'.pdf'),lang.lower())
    name='Signals_for_Next_Season_2027_Guide_KO'
    (OUT/(name+'.md')).write_text(GUIDE_KO)
    (OUT/(name+'.html')).write_text(render_html(GUIDE_KO,'ko'))
    pdf(GUIDE_KO,OUT/(name+'.pdf'),'ko',guide=True)
    full_report_html()
    print('Created English HTML, bilingual summaries (PDF/HTML/MD), and Korean guide (PDF/HTML/MD).')

if __name__=='__main__':main()
