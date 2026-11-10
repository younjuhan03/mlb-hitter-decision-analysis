"""Official, cached regular-season hitter inputs for the 2027 watchlist."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from datetime import datetime, timezone
import hashlib, json, time, io
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'data/raw'
YEARS=list(range(2015,2027))
COLUMNS='pa,ab,hit,home_run,batting_avg,slg_percent,on_base_percent,woba,xwoba,k_percent,bb_percent,exit_velocity_avg,launch_angle_avg,barrel_batted_rate,hard_hit_percent,oz_swing_percent,whiff_percent'

def fetch(name,url,kind='csv'):
    path=RAW/(name+'.'+kind); RAW.mkdir(parents=True,exist_ok=True)
    if path.exists():return path
    for attempt in range(3):
        try:
            with urlopen(Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=90) as response: data=response.read()
            if kind=='csv':
                parsed=pd.read_csv(io.BytesIO(data))
                if 'player_id' not in parsed or len(parsed)<100:raise ValueError('Invalid leaderboard')
            else: json.loads(data)
            path.write_bytes(data)
            path.with_suffix('.meta.json').write_text(json.dumps({'url':url,'retrieved_at_utc':datetime.now(timezone.utc).isoformat(),'sha256':hashlib.sha256(data).hexdigest()},indent=2))
            return path
        except Exception:
            if attempt==2:raise
            time.sleep(2**attempt)

def run():
    tasks=[]
    for year in YEARS:
        tasks.append((f'custom_{year}','https://baseballsavant.mlb.com/leaderboard/custom?'+urlencode({'type':'batter','year':year,'min':1,'selections':COLUMNS,'csv':'true'}),'csv'))
        tasks.append((f'expected_{year}','https://baseballsavant.mlb.com/leaderboard/expected_statistics?'+urlencode({'type':'batter','year':year,'min':1,'csv':'true'}),'csv'))
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures=[pool.submit(fetch,*task) for task in tasks]
        for i,f in enumerate(as_completed(futures),1):print(f'{i}/{len(tasks)} cached {f.result().name}',flush=True)
    ids=sorted({int(v) for year in YEARS for v in pd.read_csv(RAW/f'custom_{year}.csv').player_id})
    for i,start in enumerate(range(0,len(ids),200)):
        batch=ids[start:start+200]
        fetch(f'people_{i}','https://statsapi.mlb.com/api/v1/people?'+urlencode({'personIds':','.join(map(str,batch)),'hydrate':'currentTeam'}),'json')
        print('Player identity batch',i,'cached',flush=True)
    fetch('schedule_2026','https://statsapi.mlb.com/api/v1/schedule?'+urlencode({'sportId':1,'season':2026,'gameType':'R'}),'json')
    fetch('mlb_hitting_2026','https://statsapi.mlb.com/api/v1/stats?'+urlencode({'stats':'season','group':'hitting','season':2026,'sportIds':1,'playerPool':'ALL','limit':2000,'gameType':'R'}),'json')
    print('Official inputs ready.',flush=True)

if __name__=='__main__':run()
