#!/usr/bin/env python3
"""DEV only. Per-player league detail for the projections page. Writes data/league-s50.json."""
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
import html
import re
from collections import Counter
import requests
SEASON=50
GAMES=f"https://www.lichess4545.com/api/get_season_games/?league=team4545&include_unplayed=true&season={SEASON}"
OUT=Path(f"data/league-s{SEASON}.json")
PAIRINGS=f"https://www.lichess4545.com/team4545/season/{SEASON}/pairings/"
def pairing_details(round_number):
    # Numeric team ids from the league site's own team filter. Names are only lookup keys; duplicate names get no id.
    try:
        r=requests.get(f"https://www.lichess4545.com/team4545/season/{SEASON}/round/{round_number}/pairings/",timeout=30); r.raise_for_status()
        pairs=[(html.unescape(n).strip(),int(i)) for i,n in re.findall(rf'href="/team4545/season/{SEASON}/round/{round_number}/pairings/team/(\d+)/">([^<]+)</a>',r.text)]
        count=Counter(n for n,_ in pairs)
        boards={}
        for section in re.split(r'(?=<tr\b[^>]*class="header-row")',r.text)[1:]:
            rows=re.findall(r'<tr\b[^>]*>(.*?)</tr>',section,re.S)
            for board,row in enumerate(rows[1:9],1):
                for handle in re.findall(rf'href="/team4545/season/{SEASON}/player/([^/]+)/"',row):
                    boards[html.unescape(handle).casefold()]=board
        return {n:i for n,i in pairs if count[n]==1},boards
    except Exception as e:
        print(f'pairing details unavailable: {e}'); return {},{}
def expectancy(a,b): return 1/(1+10**(-(a-b)/400))
def pregame_ratings(game_ids):
    # PGN Elo tags are fixed when the game starts. Never infer historical odds from live ratings.
    cached={}
    if OUT.exists():
        try: cached=json.loads(OUT.read_text()).get('pregame_games',{})
        except (ValueError,OSError): pass
    missing=[gid for gid in game_ids if gid not in cached]
    for i in range(0,len(missing),300):
        try:
            r=requests.post('https://lichess.org/api/games/export/_ids?moves=false&clocks=false&evals=false&opening=false',
                data=','.join(missing[i:i+300]),headers={'Content-Type':'text/plain','Accept':'application/x-chess-pgn'},timeout=45)
            r.raise_for_status()
            for game in re.split(r'(?=\[Event )',r.text):
                tags=dict(re.findall(r'^\[(\w+) "([^"]*)"\]$',game,re.M))
                gid=tags.get('GameId')
                if gid in game_ids and tags.get('WhiteElo','').isdigit() and tags.get('BlackElo','').isdigit():
                    cached[gid]={'white':int(tags['WhiteElo']),'black':int(tags['BlackElo'])}
        except requests.RequestException as e:
            print(f'pregame ratings unavailable: {e}')
    return cached
def score(v):
    v=str(v or '').strip().lower()
    if v in ('1-0','1x-0f','1','1.0'): return (1.0,0.0)
    if v in ('0-1','0f-1x','0'): return (0.0,1.0)
    if v in ('1/2-1/2','1/2z-1/2z','½-½','0.5-0.5','draw'): return (0.5,0.5)
    return None
def main():
    raw=requests.get(GAMES,timeout=30).json()['games']
    current=max((int(g.get('round') or 0) for g in raw),default=0)
    prior=defaultdict(float)
    for g in raw:
        r=int(g.get('round') or 0); d=score(g.get('result'))
        if r<current and d:
            prior[str(g.get('white_team') or '').strip()]+=d[0]; prior[str(g.get('black_team') or '').strip()]+=d[1]
    games=[g for g in raw if int(g.get('round') or 0)==current]
    handles=sorted({str(g.get(k) or '').strip() for g in games for k in ('white','black') if g.get(k)})
    ratings={}
    rated_handles=set()
    for i in range(0,len(handles),300):
        r=requests.post('https://lichess.org/api/users',data=','.join(handles[i:i+300]),headers={'Accept':'application/json'},timeout=30); r.raise_for_status()
        for u in r.json():
            handle=(u.get('username') or u.get('id','')).casefold()
            rating=u.get('perfs',{}).get('classical',{}).get('rating')
            if isinstance(rating,(int,float)) and 0<rating<4000:
                rated_handles.add(handle)
            ratings[handle]=rating if rating is not None else 1500
    game_ids={str(g.get('game_id') or '').strip() for g in games if g.get('game_id')}
    pregames=pregame_ratings(game_ids)
    teams=defaultdict(lambda:{'players':[]})
    for g in games:
        w=str(g.get('white') or '').strip(); b=str(g.get('black') or '').strip(); wt=str(g.get('white_team') or '').strip(); bt=str(g.get('black_team') or '').strip()
        if not w or not b: continue
        d=score(g.get('result')); gid=str(g.get('game_id') or '').strip() or None
        start=pregames.get(gid) if gid else None
        before=expectancy(start['white']+25,start['black']) if start else None
        live_estimate=(expectancy(ratings[w.casefold()]+25,ratings[b.casefold()])
                       if d is None and before is None and w.casefold() in rated_handles and b.casefold() in rated_handles else None)
        if d is None:
            we=expectancy(ratings.get(w.casefold(),1500)+25,ratings.get(b.casefold(),1500)); exp=(we,1-we)
        else: exp=d
        for me,opp,team,oteam,color,i in ((w,b,wt,bt,'white',0),(b,w,bt,wt,'black',1)):
            a=None if d is None else d[i]
            teams[team]['players'].append({'handle':me,'color':color,'opponent':opp,'opponent_team':oteam,'rating':ratings.get(me.casefold()),'expected_points':exp[i],'pregame_expectation':(before if i==0 else 1-before) if before is not None else None,'live_elo_estimate':(live_estimate if i==0 else 1-live_estimate) if live_estimate is not None else None,'pregame_ratings':start,'actual_result':a,'status':'pending' if a is None else 'won' if a==1 else 'draw' if a==0.5 else 'lost','game_url':f'https://lichess.org/{gid}' if gid else None})
    ids,boards=pairing_details(current)
    out={}
    for n in sorted(set(teams)|set(prior)):
        if not n: continue
        ps=teams[n]['players']
        ps.sort(key=lambda p:(boards.get(p['handle'].casefold(),99),p['handle'].casefold()))
        out[n]={'prior_actual':prior[n],'round_projected':sum(p['expected_points'] for p in ps),'players':ps}
        if n in ids: out[n]['team_id']=ids[n]
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps({'season':SEASON,'round':current,'updated_at':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),'teams':out,'pregame_games':pregames},separators=(',',':'),ensure_ascii=False)+'\n')
    print(f'League detail for {len(out)} teams, round {current}')
if __name__=='__main__': main()
