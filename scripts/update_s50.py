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

# *** NEXT SEASON (see SEASON-FLIP.md for the full plain-language guide):
# 1. Copy this file to update_s<NN>.py (e.g. update_s51.py).
# 2. Change SEASON below to the new season number.
# 3. In ENTRIES, change "sheet=S50Entries" to the new entries tab name.
# 4. Change the two "s50" filenames in OUT and PRICES to the new season.
# 5. Add the new script and data files to .github/workflows/update.yml.
SEASON = 50  # <== UPDATE EACH SEASON
ROUNDS = 8
SHEET = "1l4XTRMISXTYiFgV_vD68v3svJnI-Yroo0_q8MaSGYL4"  # league spreadsheet; same every season
PAIRINGS = f"https://www.lichess4545.com/team4545/season/{SEASON}/round/{{round}}/pairings/"
ENTRIES = f"https://docs.google.com/spreadsheets/d/{SHEET}/gviz/tq?tqx=out:csv&sheet=S50Entries"  # <== UPDATE EACH SEASON (tab name)
OUT = Path(__file__).resolve().parent.parent / "data" / "standings-s50.json"  # <== UPDATE EACH SEASON
PRICES = Path(__file__).resolve().parent.parent / "data" / "prices-s50.json"  # <== UPDATE EACH SEASON

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
    bots.append(mk("On the dot", f"A random {target:,} Team", best[1]))
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
            known = {p["handle"].casefold(): p for p in boards[b]}
            winner = next((h for h in order if counts[h] == top and h.casefold() in known), None)
            picks.append(known[winner.casefold()] if winner else None)
        if all(picks):
            bots.insert(0, mk("popularity", "Most Popular Players Team", picks))
    return bots


def parse_entries(csv_text):
    """Header-aware parse of the S50 Entries tab. Supports both the app header
    (Timestamp, Owner, Team name, Board 1..8, Total) and the prior-season sheet
    layout (blank owner col, Fantasy Team, Board 1..10, Total Price, Date
    Submitted). Returns [] when the tab is not an entries tab (gviz fallback)."""
    rows = list(csv.reader(io.StringIO(csv_text)))
    if not rows:
        return []
    hdr = [h.strip().lower() for h in rows[0]]

    def col(names, default=None):
        for n in names:
            if n in hdr:
                return hdr.index(n)
        return default

    board_cols = [col(["board %d" % b, "board %d " % b]) for b in range(1, 9)]
    # gviz silently returns the workbook's default tab when the S50 tab is
    # missing. Accept only a real entries header: the app header ("owner")
    # or the prior-season layout (blank first cell + "fantasy team"). The
    # default Standings tab ("player name" / "total points") is rejected.
    entries_header = "owner" in hdr or ((hdr[0] == "" if hdr else False) and "fantasy team" in hdr)
    if any(c is None for c in board_cols) or not entries_header or "total points" in hdr:
        print("Entries tab not found yet (gviz fell back to another tab); 0 teams")
        return []
    owner_col = col(["owner"], 0)
    name_col = col(["team name", "fantasy team"])
    total_col = col(["total", "total price"])

    bot_owners = {"popularity", "cheapskate", "profligate", "arbitrary", "on the dot"}
    out = []
    for row in rows[1:]:
        if len(row) <= max(owner_col, max(board_cols)) or not row[owner_col].strip():
            continue
        owner = row[owner_col].strip()
        # rows owned by the synthetic entries (carried over when the tab was
        # duplicated from a prior season) are not real entries: they never
        # appear on the site from the sheet and never feed the popularity count
        if owner.casefold() in bot_owners:
            continue
        roster = [row[c].strip() for c in board_cols if c < len(row) and row[c].strip()]
        total = None
        if total_col is not None and len(row) > total_col and row[total_col].strip():
            try: total = int(float(re.sub(r"[^\d.]", "", row[total_col])))
            except ValueError: total = None
        name = row[name_col].strip() if name_col is not None and len(row) > name_col else ""
        out.append({"owner": owner,
                    "name": name or f"{owner}’s team",
                    "handles": roster, "total": total})
    return out

def main():
    players = defaultdict(lambda: {"points": 0.0, "games": 0})
    total_pairings = 0
    cur_round = 0
    cur_played = 0
    cur_sched = 0
    cur_sched_by = defaultdict(int)
    for rnd in range(1, ROUNDS + 1):
        html = try_fetch(PAIRINGS.format(round=rnd))
        if not html:
            continue
        p = Tables(); p.feed(html)
        rnd_sched = 0
        rnd_played = 0
        rnd_sched_by = defaultdict(int)
        rnd_played_by = defaultdict(int)
        for cells in p.rows:
            if len(cells) != 4 or not re.search(r" \(\d+\)$", cells[0]) or not re.search(r" \(\d+\)$", cells[2]):
                continue
            left = re.sub(r" \(\d+\)$", "", cells[0]); right = re.sub(r" \(\d+\)$", "", cells[2])
            rnd_sched += 1
            rnd_sched_by[left.casefold()] += 1
            rnd_sched_by[right.casefold()] += 1
            raw_score = cells[1].replace(" ", "")
            scores = [raw_score[:len(raw_score)//2], raw_score[len(raw_score)//2:]]
            if len(scores) != 2 or not scores[0] or not scores[1] or scores[0][0] not in "01½" or scores[1][0] not in "01½":
                continue
            total_pairings += 1
            rnd_played += 1
            for handle, raw in ((left, scores[0]), (right, scores[1])):
                key = handle.casefold()
                players[key]["points"] += {"0": 0.0, "½": 0.5, "1": 1.0}[raw[0]]
                players[key]["games"] += 1
                rnd_played_by[key] += 1
        if rnd_sched:
            cur_round, cur_sched, cur_played = rnd, rnd_sched, rnd_played
            cur_sched_by = rnd_sched_by
            cur_played_by = rnd_played_by

    def games_left(roster):
        if not cur_round:
            return 0
        return sum(max(0, cur_sched_by.get(p.casefold(), 0) - cur_played_by.get(p.casefold(), 0)) for p in roster)

    teams = []
    real_for_bots = []
    csv_text = try_fetch(ENTRIES)
    if csv_text and not csv_text.lstrip().startswith("<"):
        for e in parse_entries(csv_text):
            owner, name, roster, total = e["owner"], e["name"], e["handles"], e["total"]
            real_for_bots.append({"handles": roster})
            pts = sum(players[p.casefold()]["points"] for p in roster)
            games = sum(players[p.casefold()]["games"] for p in roster)
            teams.append({"owner": owner, "name": name, "total": total, "points": pts, "games": games,
                          "games_left": games_left(roster),
                          "ppg": pts / games if games else 0,
                          "roster": [{"handle": p, "points": players[p.casefold()]["points"],
                                      "games": players[p.casefold()]["games"]} for p in roster]})
    for b in bot_teams(real_for_bots):
        roster = b["handles"]
        pts = sum(players[p.casefold()]["points"] for p in roster)
        games = sum(players[p.casefold()]["games"] for p in roster)
        teams.append({"owner": b["owner"], "name": b["name"], "bot": True, "total": b["total"],
                      "points": pts, "games": games, "games_left": games_left(roster), "ppg": pts / games if games else 0,
                      "roster": [{"handle": h, "points": players[h.casefold()]["points"],
                                  "games": players[h.casefold()]["games"]} for h in roster]})
    # League tiebreaks: 1) points per game, 2) lowest total price.
    # Ranks stay shared while no games are played (0-0 with no games means
    # PPG is undefined for everyone, so price does not order anyone yet).
    INF = float("inf")
    popular = []
    for b in range(8):
        counts = {}
        for e in real_for_bots:
            if b < len(e["handles"]):
                h = e["handles"][b]
                counts[h] = counts.get(h, 0) + 1
        if counts:
            top = max(counts.values())
            popular.append({"board": b + 1, "handle": next(h for h in counts if counts[h] == top),
                            "picks": top, "of": len(real_for_bots)})
    teams.sort(key=lambda x: (-x["points"], -x["ppg"],
                              x["total"] if x["total"] is not None else INF,
                              x["owner"].casefold()))
    rank = 0; last = None
    for i, t in enumerate(teams, 1):
        if t["games"] == 0:
            key = ("preseason", t["points"])  # shared rank until games exist
        else:
            key = (t["points"], t["ppg"], t["total"])
        if key != last:
            rank = i; last = key
        t["rank"] = rank
    payload = {
        "season": SEASON, "rounds": ROUNDS,
        "updated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source": {"pairings": f"https://www.lichess4545.com/team4545/season/{SEASON}/pairings/", "entries": ENTRIES},
        "method": "Everyone starts at 0 until round 1 pairings are published. Points from live pairings; ties: points per game, then lowest total team price.",
        "pairings_parsed": total_pairings, "popular": popular, "teams": teams,
        "round": {"number": cur_round, "played": cur_played, "total": cur_sched},
    }
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    print(f"Updated S50: {len(teams)} teams from {total_pairings} pairings")

if __name__ == "__main__":
    main()
