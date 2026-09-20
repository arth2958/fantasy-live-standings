#!/usr/bin/env python3
"""Build Season 50 fantasy player prices from the live lichess4545 roster page.

Pricing (reverse-engineered from the league's S49 spreadsheet and verified
against every cached price there):
    price = max(200, roundup(2000 - (center - expected_score) * 200))
    expected_score = sum over every OTHER player on the same board of
                     1 / (1 + 10 ** ((opp_rating - rating) / 400))
    center = (teams - 1) / 2

Registrations move until the season closes, so this script is meant to be
re-run (the GitHub Action does so on a schedule) until the roster freezes.
"""
import json, math, re, time, urllib.request
from datetime import datetime, timezone
from html import unescape
from pathlib import Path

SEASON = 50
ROSTERS = f"https://www.lichess4545.com/team4545/season/{SEASON}/rosters/"
OUT = Path(__file__).resolve().parent.parent / "data" / f"prices-s{SEASON}.json"
MIN_PRICE = 200
BASE_PRICE = 2000
STEP = 200

def fetch(url):
    bust = f"{url}?_={int(time.time())}"
    req = urllib.request.Request(bust, headers={
        "User-Agent": "FantasyEntries/1.0 (+https://github.com/arth2958/fantasy-live-standings)",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")

def parse_rosters(html):
    body = html[html.find("<tbody"):]
    teams = []
    in_alternates = False
    for row in re.split(r"<tr>", body)[1:]:
        if "alternates" in row.lower() and "cell-team" in row:
            in_alternates = True
        if in_alternates:
            continue
        mteam = re.search(r'class="team-link"[^>]*>([^<]+)</a>', row)
        if not mteam:
            continue
        players = re.findall(rf'/team4545/season/{SEASON}/player/([^/"]+)/">([^<]+)</a>', row)
        ratings = re.findall(r'<td class="cell-rating">\s*(\d+)\s*</td>', row)
        if len(players) != 8 or len(ratings) != 8:
            raise SystemExit(f"Incomplete roster row for team {mteam.group(1)!r}: "
                             f"{len(players)} players, {len(ratings)} ratings")
        teams.append((unescape(mteam.group(1)).strip(),
                      [(disp.strip(), int(rtg)) for (slug, disp), rtg in zip(players, ratings)]))
    if len(teams) < 2:
        raise SystemExit(f"Only {len(teams)} complete team rows parsed; page layout may have changed")
    return teams

def build(teams):
    n = len(teams)
    center = (n - 1) / 2
    boards = []
    for b in range(8):
        rated = [(handle, rtg) for _, players in teams for handle, rtg in [players[b]]]
        players = []
        for i, (handle, rtg) in enumerate(rated):
            expected = sum(
                1 / (1 + 10 ** ((o_rtg - rtg) / 400))
                for j, (_, o_rtg) in enumerate(rated) if j != i
            )
            price = max(MIN_PRICE, math.ceil(BASE_PRICE - (center - expected) * STEP))
            players.append({"handle": handle, "rating": rtg, "price": price})
        players.sort(key=lambda p: (-p["rating"], p["handle"].lower()))
        boards.append({"board": b + 1, "players": players})
    return center, boards

def main():
    html = fetch(ROSTERS)
    teams = parse_rosters(html)
    center, boards = build(teams)
    data = {
        "season": SEASON,
        "source": ROSTERS,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "team_count": len(teams),
        "center": center,
        "provisional": True,
        "note": "Prices regenerate from the live roster until registration closes; "
                "freeze the final JSON when the season locks.",
        "boards": boards,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, indent=1) + "\n")
    for b in boards:
        prices = [p["price"] for p in b["players"]]
        print(f"Board {b['board']}: n={len(prices)} avg={sum(prices)/len(prices):.2f} "
              f"min={min(prices)} max={max(prices)} floor_hits={sum(1 for p in prices if p == MIN_PRICE)}")
    print(f"Wrote {OUT} ({len(teams)} teams, center {center})")

if __name__ == "__main__":
    main()
