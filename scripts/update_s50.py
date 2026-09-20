#!/usr/bin/env python3
"""Build Season 50 fantasy standings.

Entries come from the league sheet's "S50 Entries" tab (written by the
Apps Script collector). Pairings come from the public S50 round pages; the
season has not started, so missing pages are tolerated and everyone sits at
0 points until games land.
"""
import csv, io, json, random, re, urllib.request, urllib.error
from collections import defaultdict
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

SEASON = 50
ROUNDS = 8
SHEET = "1l4XTRMISXTYiFgV_vD68v3svJnI-Yroo0_q8MaSGYL4"
PAIRINGS = f"https://www.lichess4545.com/team4545/season/{SEASON}/round/{{round}}/pairings/"
ENTRIES = f"https://docs.google.com/spreadsheets/d/{SHEET}/gviz/tq?tqx=out:csv&sheet=S50%20Entries"
OUT = Path(__file__).resolve().parent.parent / "data" / "standings-s50.json"
PRICES = Path(__file__).resolve().parent.parent / "data" / "prices-s50.json"

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "FantasyStandings/1.0 (+https://github.com/arth2958/fantasy-live-standings)"})
    with urllib.request.urlopen(req, timeout=45) as r:
        return r.read().decode("utf-8")

def try_fetch(url):
    try:
        return fetch(url)
    except Exception as e:
        print(f"skip {url}: {e}")
        return None

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

def bot_teams(real_teams):
    """The five synthetic entries, computed from the locked S50 price snapshot.
    Rules replicate the league sheet's S49 Entries tab rows 2-6.
    Bots are never eligible to win; the budget cap does not apply to them."""
    data = json.loads(PRICES.read_text())
    boards = [b["players"] for b in data["boards"]]
    if any(not b for b in boards):
        return []
    rng = random.Random(50)  # fixed seed: arbitrary stays the same team every run
    bots = []
    def mk(owner, name, picks):
        return {"owner": owner, "name": name, "bot": True,
                "total": sum(p["price"] for p in picks),
                "handles": [p["handle"] for p in picks]}
    bots.append(mk("cheapskate", "Lowest Cost Team",
                   [min(b, key=lambda p: p["price"]) for b in boards]))
    bots.append(mk("profligate", "Highest Cost Team",
                   [max(b, key=lambda p: p["price"]) for b in boards]))
    bots.append(mk("arbitrary", "Random Team", [rng.choice(b) for b in boards]))
    # On the dot: random team using the full 16,000 budget (exactly if possible).
    target = 16000
    best = None
    for _ in range(400000):
        picks = [rng.choice(b) for b in boards]
        t = sum(p["price"] for p in picks)
        if best is None or abs(t - target) < abs(best[0] - target):
            best = (t, picks)
        if t == target:
            break
    bots.append(mk("On the dot", f"A random €{target:,} Team", best[1]))
    # popularity: most-picked player per board across real entries, in sheet
    # order (MATCH returns the first max-count cell, i.e. earliest entry wins ties).
    if real_teams:
        picks = []
        for b in range(8):
            counts, order = {}, []
            for t in real_teams:
                h = t["handles"][b] if b < len(t["handles"]) else None
                if not h:
                    continue
                if h not in counts:
                    order.append(h)
                counts[h] = counts.get(h, 0) + 1
            top = max(counts.values()) if counts else 0
            winner = next((h for h in order if counts[h] == top), None)
            picks.append(next(p for p in boards[b] if p["handle"] == winner) if winner else None)
        if all(picks):
            bots.insert(0, mk("popularity", "Most Popular Players Team", picks))
    return bots

def main():
    players = defaultdict(lambda: {"points": 0.0, "games": 0})
    total_pairings = 0
    for rnd in range(1, ROUNDS + 1):
        html = try_fetch(PAIRINGS.format(round=rnd))
        if not html:
            continue
        p = Tables(); p.feed(html)
        for cells in p.rows:
            if len(cells) != 4 or not re.search(r" \(\d+\)$", cells[0]):
                continue
            left = re.sub(r" \(\d+\)$", "", cells[0]); right = re.sub(r" \(\d+\)$", "", cells[2])
            raw_score = cells[1].replace(" ", "")
            scores = [raw_score[:len(raw_score)//2], raw_score[len(raw_score)//2:]]
            if len(scores) != 2 or scores[0][0] not in "01½" or scores[1][0] not in "01½":
                continue
            total_pairings += 1
            for handle, raw in ((left, scores[0]), (right, scores[1])):
                key = handle.casefold()
                players[key]["points"] += {"0": 0.0, "½": 0.5, "1": 1.0}[raw[0]]
                players[key]["games"] += 1

    teams = []
    csv_text = try_fetch(ENTRIES)
    if csv_text and not csv_text.lstrip().startswith("<"):
        rows = list(csv.reader(io.StringIO(csv_text)))
        header_ok = rows and len(rows[0]) >= 3 and rows[0][0].strip().lower() == "timestamp" and rows[0][1].strip().lower() == "owner"
        if not header_ok:
            print("Entries tab not found yet (gviz fell back to another tab); 0 teams")
            rows = []
        for row in rows[1:]:
            # Timestamp, Owner, Team name, Board 1..8, Total
            if len(row) < 11 or not row[1].strip():
                continue
            owner, name = row[1].strip(), row[2].strip()
            roster = [x.strip() for x in row[3:11] if x.strip()]
            pts = sum(players[p.casefold()]["points"] for p in roster)
            games = sum(players[p.casefold()]["games"] for p in roster)
            teams.append({"owner": owner, "name": name, "points": pts, "games": games,
                          "ppg": pts / games if games else 0,
                          "roster": [{"handle": p, "points": players[p.casefold()]["points"],
                                      "games": players[p.casefold()]["games"]} for p in roster]})
    real_for_bots = []
    csv_text2 = csv_text
    if csv_text2 and not csv_text2.lstrip().startswith("<"):
        rows = list(csv.reader(io.StringIO(csv_text2)))
        if rows and len(rows[0]) >= 3 and rows[0][0].strip().lower() == "timestamp":
            for row in rows[1:]:
                if len(row) >= 11 and row[1].strip():
                    real_for_bots.append({"handles": [x.strip() for x in row[3:11] if x.strip()]})
    for b in bot_teams(real_for_bots):
        roster = b["handles"]
        pts = sum(players[p.casefold()]["points"] for p in roster)
        games = sum(players[p.casefold()]["games"] for p in roster)
        teams.append({"owner": b["owner"], "name": b["name"], "bot": True, "total": b["total"],
                      "points": pts, "games": games, "ppg": pts / games if games else 0,
                      "roster": [{"handle": h, "points": players[h.casefold()]["points"],
                                  "games": players[h.casefold()]["games"]} for h in roster]})
    teams.sort(key=lambda x: (-x["points"], -x["ppg"], x["owner"].casefold()))
    rank = 0; last = None
    for i, t in enumerate(teams, 1):
        key = (t["points"], t["ppg"])
        if key != last:
            rank = i; last = key
        t["rank"] = rank
    payload = {
        "season": SEASON, "rounds": ROUNDS,
        "updated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source": {"pairings": f"https://www.lichess4545.com/team4545/season/{SEASON}/pairings/", "entries": ENTRIES},
        "method": "Everyone starts at 0 until round 1 pairings are published. Points from live pairings; ties: fantasy points per game.",
        "pairings_parsed": total_pairings, "teams": teams,
    }
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    print(f"Updated S50: {len(teams)} teams from {total_pairings} pairings")

if __name__ == "__main__":
    main()
