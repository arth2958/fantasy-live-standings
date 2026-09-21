#!/usr/bin/env python3
"""Isolated S50 rating projection. Writes only data/projections-s50.json."""
import json, math, os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
import requests
SEASON=50
GAMES=f"https://www.lichess4545.com/api/get_season_games/?league=team4545&include_unplayed=true&season={SEASON}"
STANDINGS=Path("data/standings-s50.json")
OUT=Path("data/projections-s50.json")

def expectancy(a,b): return 1/(1+10**(-(a-b)/400))
def score(v):
    v=str(v or '').strip().lower()
    if v in ('1-0','1','1.0'): return (1.0,0.0)
    if v in ('0-1','0'): return (0.0,1.0)
    if v in ('1/2-1/2','½-½','0.5-0.5','draw'): return (0.5,0.5)
    return None

def main():
    standings=json.loads(STANDINGS.read_text())
    raw=requests.get(GAMES,timeout=30).json()['games']
    current=max((int(g.get('round') or 0) for g in raw),default=0)
    games=[g for g in raw if int(g.get('round') or 0)==current]
    handles=sorted({str(g.get(k) or '').strip() for g in games for k in ('white','black') if g.get(k)})
    ratings={}
    for i in range(0,len(handles),300):
        r=requests.post('https://lichess.org/api/users',data=','.join(handles[i:i+300]),headers={'Accept':'application/json'},timeout=30)
        r.raise_for_status()
        for u in r.json():
            p=u.get('perfs',{}).get('classical',{})
            ratings[(u.get('username') or u.get('id','')).casefold()]={'rating':p.get('rating',1500),'rd':p.get('rd',350),'games':p.get('games',0),'provisional':bool(p.get('prov'))}
    player_proj=defaultdict(float); player_actual=defaultdict(float); player_left=defaultdict(int)
    league=defaultdict(lambda:{'projected':0.0,'actual':0.0,'paired':0,'left':0})
    for g in games:
        w=str(g.get('white') or '').strip(); b=str(g.get('black') or '').strip(); wt=str(g.get('white_team') or '').strip(); bt=str(g.get('black_team') or '').strip()
        if not w or not b: continue
        wk,bk=w.casefold(),b.casefold(); done=score(g.get('result'))
        if done is None:
            wr=ratings.get(wk,{'rating':1500})['rating']; br=ratings.get(bk,{'rating':1500})['rating']
            we=expectancy(wr+25,br); vals=(we,1-we); player_left[wk]+=1; player_left[bk]+=1; league[wt]['left']+=1; league[bt]['left']+=1
        else: vals=done; player_actual[wk]+=vals[0]; player_actual[bk]+=vals[1]; league[wt]['actual']+=vals[0]; league[bt]['actual']+=vals[1]
        player_proj[wk]+=vals[0]; player_proj[bk]+=vals[1]; league[wt]['projected']+=vals[0]; league[bt]['projected']+=vals[1]; league[wt]['paired']+=1; league[bt]['paired']+=1
    fantasy=[]
    for t in standings['teams']:
        if t.get('bot'): continue
        roster=[p['handle'] for p in t['roster']]
        pending=sum(player_proj[h.casefold()]-player_actual[h.casefold()] for h in roster)
        fantasy.append({'owner':t['owner'],'name':t['name'],'actual_points':t['points'],'projected_points':t['points']+pending,'projected_round':sum(player_proj[h.casefold()] for h in roster),'left':sum(player_left[h.casefold()] for h in roster),'paired':sum(1 for h in roster if h.casefold() in player_proj)})
    fantasy.sort(key=lambda x:(-x['projected_points'],x['owner'].casefold()))
    for i,t in enumerate(fantasy,1): t['projected_rank']=i
    league_rows=[{'name':n,**v,'eligible':False} for n,v in league.items() if n]
    league_rows.sort(key=lambda x:(-x['projected'],x['name'].casefold()))
    payload={'season':SEASON,'round':current,'updated_at':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),'method':'Expected game points from live Lichess Classical ratings (Elo, +25 for White); completed games use actual results.','fantasy_teams':fantasy,'league_teams':league_rows,'ratings':{'pool':'classical','players':len(ratings)}}
    OUT.parent.mkdir(exist_ok=True); OUT.write_text(json.dumps(payload,indent=2,ensure_ascii=False)+'\n')
    print(f"Projected {len(fantasy)} fantasy teams and {len(league_rows)} league teams for round {current}")
if __name__=='__main__': main()
