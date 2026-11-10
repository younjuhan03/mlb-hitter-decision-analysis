"""Apply the 2026-10-04 presentation corrections to the supplied English PDF.

Run python -m src.review_presentation after src.review_verification.
Requires PyMuPDF and matplotlib; preserves frozen analytical inputs and outputs.
"""
from pathlib import Path
import base64, gzip, hashlib, json, re
import fitz
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
FONT=str(ROOT/'reference/DejaVuSans.ttf')
MONO=str(ROOT/'reference/DejaVuSansMono.ttf')

def replace(doc, page_number, rect, content, size=11, fill=(1,1,1), mono=False):
    page=doc[page_number-1]
    rect=fitz.Rect(rect)
    page.add_redact_annot(rect,fill=fill)
    page.apply_redactions(images=0,graphics=0)
    font_name='ReviewMono' if mono else 'ReviewSans'
    page.insert_font(fontname=font_name,fontfile=MONO if mono else FONT)
    remaining=page.insert_textbox(rect,content,fontname=font_name,fontsize=size,
        color=(.141,.239,.294),lineheight=1.23)
    if remaining<0:
        raise ValueError(f'Page {page_number}: overflow {remaining}: {content[:80]}')

def chart():
    output=ROOT/'reports/model_comparison.png'
    old=base64.b64encode((ROOT/'reference/model_comparison_original.png').read_bytes()).decode()
    metrics=pd.read_csv(ROOT/'reports/model_metrics.csv')
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(1,2,figsize=(10,4),layout='constrained')
    for scope,ax,title in zip(['development','final_2026'],axes,['Expanding tests: 2022-2025','Most recent year: 2026']):
        d=metrics.loc[metrics.scope.eq(scope)].set_index('model').loc[['B0_carry','M1_results','M2_levels','M3_changes']]
        bars=ax.bar(['B0','M1','M2','M3'],d.rmse,color=['#b5c4cd','#617786','#2b918d','#e59b42'])
        ax.set_ylim(0,.045);ax.set_title(title,fontweight='bold');ax.grid(axis='y',alpha=.12);ax.set_axisbelow(True)
        for b,v in zip(bars,d.rmse):ax.text(b.get_x()+b.get_width()/2,v+.0007,f'{v:.5f}',ha='center',fontsize=9,color='#243d4b')
        ax.set_ylabel('RMSE: next-season wOBA')
    fig.savefig(output,dpi=180);plt.close(fig)
    return old,base64.b64encode(output.read_bytes()).decode()

def patch_html(text,old_chart,new_chart):
    text=text.replace(old_chart,new_chart)
    marker='<h3>Lars Nootbaar</h3>'
    if marker in text and '334PA는 양쪽 발뒤꿈치' not in text:
        start=text.index(marker);end=text.index('</article>',start)
        context='<p><strong>시즌 맥락:</strong> 334PA는 양쪽 발뒤꿈치 수술 후 6월 5일 복귀와 8월 3일 Arizona 트레이드를 겪은 표본이다. Savant에서 STL 48경기·183PA·타율 .234·3HR, Arizona 42경기·151PA·5HR, 합계 334PA와 시즌 wOBA .320을 대조했다. 건강과 시즌 내 신호의 일관성은 별도 조사한다.</p>'
        text=text[:end]+context+text[end:]
    return text

def main():
    old_chart,new_chart=chart()
    source=ROOT/'reference/Report_EN_original.pdf'
    doc=fitz.open(source)
    # Replace the figure, retaining the same metrics and plotting scale.
    doc[1].replace_image(doc[1].get_images()[0][0],filename=str(ROOT/'reports/model_comparison.png'))
    replace(doc,3,(40.5,646,799.5,666),
        'M2\u2019s development MAE was marginally worse than M1\u2019s at α=10 and lower at α=100 and 1000. M1 adoption depends on the chosen α and',size=10.7)
    replace(doc,12,(40.5,1106,799.5,1142),
        'M1 uses 9 traditional variables; M2 adds 6 skill levels; M3 adds 6 changes (9/15/21 inputs). Hard-hit, K%, BB%, and ISO already enter M1/M2. The cards restate them as evidence; only mean launch angle is newly displayed, and it is excluded from the models.',size=9.6)
    replace(doc,14,(72.75,783.5,765,805),
        'Counterevidence: 334PA after injury recovery and a trade; barrel -0.1pp. M1 .321 vs M2 .334 shows input sensitivity.',size=10.3,fill=(1,.973,.929))
    replace(doc,14,(62.25,881.5,777.75,924),
        'Season context: Returned June 5 after surgery on both heels; traded to Arizona August 3. Savant: STL 48G/183PA/.234/3HR + Arizona 42G/151PA/5HR = 334PA; season wOBA .320. Review health, opportunity, and within-season signal consistency. [P1-P3]',size=10.2)
    replace(doc,15,(40.5,562.5,799.5,581),
        'Additional observations use the existing 2025 and 2026 Custom files and processed CSVs. Mean launch angle is a summary; it cannot replace sweet-',size=9.2)
    replace(doc,24,(40.5,466.5,799.5,511),
        'Marcel uses recent 3-year history, weighting, regression to the mean, and age adjustment; its exact constants were not implemented here. Savant bat tracking covers the second half of 2023 onward [E2]; MLB introduced the public release on May 13, 2024 [E3]. Neither covers the entire 2015-2026 sample.',size=9.4)
    replace(doc,25,(40.5,332,799.5,394),
        'Even 4/5 or 5/5 successes in 2027 alone will not establish general superiority or replace M1. M1 remains the default, with at most 5 exploratory signal investigations. The rules below are retained from the supplied PDF. Its earlier addendum file and hash were absent from the supplied ZIP; no original registration claim is made.',size=11)
    replace(doc,25,(40.5,710.8,799.5,774),
        'The .025 criterion at each of two reviews is a one-sided upper-tail probability P(random successes ≥ observed). The earlier benchmark table instead uses a two-sided probability-ordered tail; these are different quantities. No extra annual adoption tests apply. The 10pp margins are analyst judgments; these operating rules do not prove superiority over M1. Usable-bat yield cannot replace growth criteria.',size=10.5)
    replace(doc,25,(40.5,781.3,799.5,863),
        'Illustration: With independent binomial sampling, random rate .24, and n=5, P(≥3)=.0933 and P(≥4)=.0134. If the true rate is .40, power to reach 4 is 8.7%. At n=15 and n=25, the .025 upper-tail rule requires 8 and 11 successes; power is 21.3% and 41.4%, respectively. Adequate power is not guaranteed. The future benchmark will use each season\u2019s finite pool and success count rather than fixing .24.',size=11)
    replace(doc,25,(40.5,871.5,799.5,908),
        'Retained rules: docs/DECISION_FOLLOWUP_RULES.md. Recomputed illustration: supplement/policy_power_illustration.csv. Current integrity checks: supplement/preservation_check.json. The original forecast and evaluation lock files are preserved.',size=9.1)
    replace(doc,26,(40.5,70.3,799.5,113),
        'Python implementation and notebook outputs are included in the companion ZIP. No public GitHub URL is supplied. The example below uses the same time split and fitting pipeline as src/study.py, with separate DataFrame and column-list names.',size=11)
    snippet='''feature_cols = MODELS["M1_results"]
train = features.loc[features.eligible_pair & features.target_season.lt(year)]
test = features.loc[features.eligible & features.target_season.eq(year)].copy()
assert train.target_season.max() < year
model = make_pipeline(
    SimpleImputer(strategy="median"), StandardScaler(), Ridge(alpha=ALPHA)
)
model.fit(train[feature_cols].to_numpy(dtype=float),
          train.target_woba.to_numpy(dtype=float))'''
    replace(doc,26,(54,133.5,786,267),snippet,size=10.3,mono=True,fill=(.965,.98,.98))
    # Correct paths that referred to files not present in the uploaded archive.
    replace(doc,26,(469,465,795,483),'src/review_verification.py, src/review_presentation.py',size=9.1,fill=(.965,.98,.98))
    replace(doc,26,(48.75,532.5,454,551),
        'Random benchmarks, power, and retained follow-up rules',size=9.1,fill=(.965,.98,.98))
    replace(doc,26,(469,532.5,799.5,551),
        'src/review_verification.py; docs/DECISION_FOLLOWUP_RULES.md',size=8.7,fill=(.965,.98,.98))
    replace(doc,26,(40.5,574.5,799.5,610),
        'Code and notebook evidence do not establish university recognition of programming coursework. Frozen forecasts and evaluation hashes were checked against the supplied ZIP: supplement/preservation_check.json. Earlier supplementary source files were not supplied.',size=9.1)
    replace(doc,26,(70.5,963.5,799.5,984),
        'PROTOCOL.md and REVISION_LOG.md; this correction is documented in docs/REVIEW_CORRECTIONS.md.',size=11)
    replace(doc,27,(40.5,32.8,799.5,136),
        'The original notebook reproduces the core analysis and Korean HTML. Run python -m src.review_verification to reproduce the new raw-data, α, random-benchmark, and power checks. Run python -m src.review_presentation to apply the PDF corrections (PyMuPDF required). The uploaded ZIP omitted earlier supplementary sources mentioned by the English PDF; this package does not claim to restore those original files. Current outputs and retained follow-up rules are included. Frozen forecasts, raw sources, and original evaluation locks are unchanged.',size=11)
    replace(doc,27,(54.75,459.8,799.5,479),
        '15. [E2] Baseball Savant - Bat Tracking: availability from the second half of 2023. Accessed 2026-10-04.',size=9.4)
    # Move the footer to make room for the verified contextual references.
    replace(doc,27,(300,550.5,550,568),'',size=9)
    refs=[
        ('[E3] MLB - Statcast bat tracking introduction, May 13, 2024.', 'https://www.mlb.com/news/what-you-need-to-know-about-statcast-bat-tracking'),
        ('[P1] Baseball Savant - Lars Nootbaar: 2026 team splits, PA, and wOBA.', 'https://baseballsavant.mlb.com/savant-player/lars-nootbaar-663457'),
        ('[P2] Field Level Media / Reuters - Nootbaar injury recovery and June 5 return, August 3, 2026.', 'https://www.reuters.com/sports/reports-cardinals-ship-lars-nootbaar-diamondbacks--flm-2026-08-03/'),
        ('[P3] Arizona Diamondbacks - Nootbaar acquisition announcement, August 3, 2026.', 'https://www.mlb.com/amp/press-release/d-backs-acquire-lars-nootbaar-from-cardinals.html')]
    for i,(label,url) in enumerate(refs):
        y=519+i*23
        replace(doc,27,(54.75,y,799.5,y+20),label,size=9.2)
        doc[26].insert_link({'kind':fitz.LINK_URI,'from':fitz.Rect(54.75,y,799.5,y+20),'uri':url})
    doc[26].insert_link({'kind':fitz.LINK_URI,'from':fitz.Rect(54.75,460,799.5,479),'uri':'https://baseballsavant.mlb.com/leaderboard/bat-tracking'})
    replace(doc,27,(275,639,640,659),'Juhan Youn - Signals for Next Season - corrected 2026-10-04',size=9.3,fill=(241/255,245/255,245/255))
    # Clarify the full-precision definition counts, preserving 33/36.
    replace(doc,5,(40.5,621.5,799.5,705),
        'M2-M1 is positive under 36/36 definitions in every period and population. M3-M2 changes direction under some definitions. Positive counts use full-precision AUC values: a difference can round to 0.000 yet be positive, so the development all-followed M3-M2 count remains 33/36. These overlapping definitions are not independent validations. All-followed success combines sufficient PA and retention; insufficient PA is decision failure, not proof of skill decline. This does not fully remove survival or opportunity selection from the wOBA model.',size=10.2)
    output=ROOT/'reports/Signals_for_Next_Season_2027_Report_EN_Corrected.pdf'
    doc.save(output,garbage=4,deflate=True);doc.close()
    # Keep both HTML sources and the self-contained notebook chart consistent.
    for path in (ROOT/'reports').glob('*.html'):
        path.write_text(patch_html(path.read_text(),old_chart,new_chart))
    notebook=ROOT/'notebooks/Signals_for_Next_Season_2027.ipynb'
    n=json.loads(notebook.read_text())
    for cell in n['cells']:
        s=''.join(cell['source'])
        match=re.search(r'SNAPSHOT_GZIP_B64 = "([^"]+)"',s)
        if match:
            payload=json.loads(gzip.decompress(base64.b64decode(match.group(1))))
            for key in ['html','body']:
                payload[key]=patch_html(payload[key],old_chart,new_chart)
            payload['charts']['model_comparison.png']=new_chart
            encoded=base64.b64encode(gzip.compress(json.dumps(payload,ensure_ascii=False).encode(),mtime=0)).decode()
            s=s[:match.start(1)]+encoded+s[match.end(1):]
            cell['source']=s.splitlines(keepends=True)
        for o in cell.get('outputs',[]):
            for key,value in o.get('data',{}).items():
                if isinstance(value,list):
                    joined=''.join(value)
                    if key=='image/png' and joined.strip()==old_chart:o['data'][key]=[new_chart]
                    elif key=='text/html':o['data'][key]=patch_html(joined,old_chart,new_chart).splitlines(keepends=True)
                elif isinstance(value,str):o['data'][key]=value.replace(old_chart,new_chart)
    notebook.write_text(json.dumps(n,ensure_ascii=False,indent=1))
    print(output)

if __name__=='__main__':main()
