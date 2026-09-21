#!/usr/bin/env python3
"""Isolated S50 rating projection. Writes only data/projections-s50.json."""
import json, math, os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
import requests
from html.parser import HTMLParser
SEASON=50
GAMES=f"https://www.lichess4545.com/api/get_season_games/?league=team4545&include_unplayed=true&season={SEASON}"
STANDINGS=Path("data/standings-s50.json")
OUT=Path("data/projections-s50.json")
ROSTERS=f"https://www.lichess4545.com/team4545/season/{SEASON}/rosters/"
class RosterHandles(HTMLParser):
    def __init__(self): super().__init__(); self.handles=set()
    def handle_starttag(self,tag,attrs):
        if tag != "a": return
        href=dict(attrs).get("href","")
        marker=f"/team4545/season/{SEASON}/player/"
        if marker in href:
            self.handles.add(href.split(marker,1)[1].strip("/").casefold())

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
    paired_handles={str(g.get(k) or '').strip().casefold() for g in games for k in ('white','black') if g.get(k)}
    rp=RosterHandles(); rp.feed(requests.get(ROSTERS,timeout=30).text); current_roster=rp.handles
    handles=sorted({str(g.get(k) or '').strip() for g in games for k in ('white','black') if g.get(k)})
    ratings={}
    for i in range(0,len(handles),300):
        r=requests.post('https://lichess.org/api/users',data=','.join(handles[i:i+300]),headers={'Accept':'application/json'},timeout=30)
        r.raise_for_status()
        for u in r.json():
            p=u.get('perfs',{}).get('classical',{})
            ratings[(u.get('username') or u.get('id','')).casefold()]={'rating':p.get('rating',1500),'rd':p.get('rd',350),'games':p.get('games',0),'provisional':bool(p.get('prov'))}
    player_proj=defaultdict(float); player_actual=defaultdict(float); player_left=defaultdict(int); round_result={}
    league=defaultdict(lambda:{'projected':0.0,'actual':0.0,'paired':0,'left':0})
    for g in games:
        w=str(g.get('white') or '').strip(); b=str(g.get('black') or '').strip(); wt=str(g.get('white_team') or '').strip(); bt=str(g.get('black_team') or '').strip()
        if not w or not b: continue
        wk,bk=w.casefold(),b.casefold(); done=score(g.get('result'))
        if done is None:
            wr=ratings.get(wk,{'rating':1500})['rating']; br=ratings.get(bk,{'rating':1500})['rating']
            we=expectancy(wr+25,br); vals=(we,1-we); player_left[wk]+=1; player_left[bk]+=1; league[wt]['left']+=1; league[bt]['left']+=1
        else: vals=done; player_actual[wk]+=vals[0]; player_actual[bk]+=vals[1]; round_result[wk]=('won' if vals[0]==1 else 'draw' if vals[0]==0.5 else 'lost'); round_result[bk]=('won' if vals[1]==1 else 'draw' if vals[1]==0.5 else 'lost'); league[wt]['actual']+=vals[0]; league[bt]['actual']+=vals[1]
        player_proj[wk]+=vals[0]; player_proj[bk]+=vals[1]; league[wt]['projected']+=vals[0]; league[bt]['projected']+=vals[1]; league[wt]['paired']+=1; league[bt]['paired']+=1
    fantasy=[]
    for t in standings['teams']:
        if t.get('bot'): continue
        roster=[p['handle'] for p in t['roster']]
        pending=sum(player_proj[h.casefold()]-player_actual[h.casefold()] for h in roster)
        fantasy.append({'owner':t['owner'],'name':t['name'],'actual_points':t['points'],'projected_points':t['points']+pending,'projected_round':sum(player_proj[h.casefold()] for h in roster),'left':sum(player_left[h.casefold()] for h in roster),'paired':sum(1 for h in roster if h.casefold() in player_proj),'roster':[{'handle':h,'status':(round_result.get(h.casefold()) or 'pending' if h.casefold() in paired_handles else 'unpaired' if h.casefold() in current_roster else 'no_longer_rostered'),'rating':ratings.get(h.casefold(),{}).get('rating'),'expected_points':player_proj.get(h.casefold(),0),'actual_result':(player_actual.get(h.casefold()) if h.casefold() in round_result else None),'season_points':next((p.get('points',0) for p in t['roster'] if p.get('handle','').casefold()==h.casefold()),0),'season_games':next((p.get('games',0) for p in t['roster'] if p.get('handle','').casefold()==h.casefold()),0)} for h in roster]})
    fantasy.sort(key=lambda x:(-x['projected_points'],x['owner'].casefold()))
    for i,t in enumerate(fantasy,1): t['projected_rank']=i
    league_rows=[{'name':n,**v,'eligible':False} for n,v in league.items() if n]
    league_rows.sort(key=lambda x:(-x['projected'],x['name'].casefold()))
    payload={'season':SEASON,'round':current,'updated_at':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),'method':'Expected game points from live Lichess Classical ratings (Elo, +25 for White); completed games use actual results.','fantasy_teams':fantasy,'league_teams':league_rows,'ratings':{'pool':'classical','players':len(ratings)}}
    OUT.parent.mkdir(exist_ok=True); OUT.write_text(json.dumps(payload,indent=2,ensure_ascii=False)+'\n')
    print(f"Projected {len(fantasy)} fantasy teams and {len(league_rows)} league teams for round {current}")
if __name__=='__main__': main()
