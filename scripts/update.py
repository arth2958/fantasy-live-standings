#!/usr/bin/env python3
"""Build fantasy standings from the public Season 49 pairings pages + Entries sheet."""
import csv, io, json, re, urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

SEASON = 49
ROUNDS = 8
PAIRINGS = f"https://www.lichess4545.com/team4545/season/{SEASON}/round/{{round}}/pairings/"
ENTRIES = "https://docs.google.com/spreadsheets/d/1l4XTRMISXTYiFgV_vD68v3svJnI-Yroo0_q8MaSGYL4/export?format=csv&gid=2102875659"

def fetch(url):
    req=urllib.request.Request(url,headers={"User-Agent":"FantasyStandings/1.0 (+https://github.com/arth2958/fantasy-live-standings)"})
    with urllib.request.urlopen(req,timeout=45) as r: return r.read().decode("utf-8")

class Tables(HTMLParser):
    def __init__(self): super().__init__(); self.depth=0; self.row=None; self.cell=None; self.rows=[]
    def handle_starttag(self,tag,attrs):
        if tag=="table": self.depth+=1
        elif self.depth and tag=="tr": self.row=[]
        elif self.row is not None and tag in ("td","th"): self.cell=[]
    def handle_data(self,data):
        if self.cell is not None: self.cell.append(data)
    def handle_endtag(self,tag):
        if tag in ("td","th") and self.cell is not None:
            self.row.append(" ".join("".join(self.cell).split())); self.cell=None
        elif tag=="tr" and self.row is not None:
            if self.row: self.rows.append(self.row)
            self.row=None
        elif tag=="table" and self.depth: self.depth-=1

def main():
    players=defaultdict(lambda:{"points":0.0,"games":0,"rounds":{}})
    total_pairings=0
    for rnd in range(1,ROUNDS+1):
        p=Tables(); p.feed(fetch(PAIRINGS.format(round=rnd)))
        for cells in p.rows:
            if len(cells)!=4 or not re.search(r" \(\d+\)$",cells[0]): continue
            left=re.sub(r" \(\d+\)$","",cells[0]); right=re.sub(r" \(\d+\)$","",cells[2])
            raw_score=cells[1].replace(" ", "")
            scores=[raw_score[:len(raw_score)//2],raw_score[len(raw_score)//2:]]
            if len(scores)!=2 or scores[0][0] not in "01½" or scores[1][0] not in "01½": continue
            total_pairings += 1
            for handle, raw in ((left,scores[0]),(right,scores[1])):
                key=handle.casefold(); points={"0":0.0,"½":0.5,"1":1.0}[raw[0]]
                players[key]["points"] += points
                # A played game is a board result without a forfeit or administrative X.
                # Adjudicated draws (Z) are games and count.
                # Games Played is sourced from the league fantasy sheet below; pairings alone do not encode its exact convention.
                played = True
                players[key]["games"] += int(played)
                players[key]["rounds"][str(rnd)]={"points":points,"played":played,"code":raw}
    rows=list(csv.reader(io.StringIO(fetch(ENTRIES))))
    sheet_standings_url="https://docs.google.com/spreadsheets/d/1l4XTRMISXTYiFgV_vD68v3svJnI-Yroo0_q8MaSGYL4/export?format=csv&gid=319976867"
    official={}
    for sr in list(csv.reader(io.StringIO(fetch(sheet_standings_url))))[1:]:
        if len(sr)>16 and sr[0].strip():
            try: official[sr[0].strip().casefold()]={"points":float(sr[2]),"games":int(float(sr[15])),"ppg_label":sr[16]}
            except (ValueError,IndexError): pass
    teams=[]
    for row in rows[1:]:
        if len(row)<10 or not row[0].strip(): continue
        owner,name=row[0].strip(),row[1].strip(); roster=[x.strip() for x in row[2:10] if x.strip() and x.strip().lower() not in ("n/a","placeholder")]
        parsed_pts=sum(players[p.casefold()]["points"] for p in roster); parsed_games=sum(players[p.casefold()]["games"] for p in roster)
        o=official.get(owner.casefold()); pts=o["points"] if o else parsed_pts; games=o["games"] if o else parsed_games
        teams.append({"owner":owner,"name":name,"points":pts,"games":games,"ppg":pts/games if games else 0,
                      "roster":[{"handle":p,"points":players[p.casefold()]["points"],"games":players[p.casefold()]["games"]} for p in roster]})
    teams.sort(key=lambda x:(-x["points"],-x["ppg"],x["owner"].casefold()))
    rank=0; last=None
    for i,t in enumerate(teams,1):
        key=(t["points"],t["ppg"])
        if key!=last: rank=i; last=key
        t["rank"]=rank
    payload={"season":SEASON,"rounds":ROUNDS,"updated_at":datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),
             "source":{"pairings":f"https://www.lichess4545.com/team4545/season/{SEASON}/pairings/","entries":ENTRIES},
             "method":"Points and games played follow the fantasy sheet; live pairings are parsed for the roster detail. Ties: fantasy points per game.",
             "pairings_parsed":total_pairings,"teams":teams}
    Path("data").mkdir(exist_ok=True); Path("data/standings.json").write_text(json.dumps(payload,indent=2,ensure_ascii=False)+"\n")
    print(f"Updated {len(teams)} teams from {total_pairings} pairings")
if __name__=="__main__": main()
