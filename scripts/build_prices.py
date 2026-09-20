#!/usr/bin/env python3
"""Season 50 fantasy player prices (league practice, per Leo):

- Ratings are pinned to a one-time snapshot (data/ratings-s50-snapshot.json).
  Rating drift on lichess afterwards is ignored.
- Prices recompute ONLY when roster composition changes before entries close
  (a team drops out, a replacement/new team joins): existing players keep
  their snapshot ratings, newcomers are priced at their live rating at join
  time, and the center is recalculated as (N-1)/2 for the new N.

Modes:
  --freeze   Take the one-time ratings snapshot from the live roster and lock
             prices (already done for S50 at 2026-09-20 11:27 UTC).
  (default)  Watch: fetch the live roster and recompute only if composition
             changed. Writes .prices-diff.txt as the commit message.
"""
import json, math, re, sys, time, urllib.request
from datetime import datetime, timezone
from html import unescape
from pathlib import Path

# *** NEXT SEASON: change the season number, then run this script once after
# the new season's rosters publish to build data/prices-s<NN>.json and the
# ratings snapshot. See SEASON-FLIP.md.
SEASON = 50  # <== UPDATE EACH SEASON
ROSTERS = f"https://www.lichess4545.com/team4545/season/{SEASON}/rosters/"
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / f"prices-s{SEASON}.json"
SNAPSHOT = ROOT / "data" / f"ratings-s{SEASON}-snapshot.json"
DIFF = ROOT / ".prices-diff.txt"
MIN_PRICE, BASE_PRICE, STEP = 200, 2000, 200

def fetch(url):
    bust = f"{url}?_={int(time.time())}"
    req = urllib.request.Request(bust, headers={
        "User-Agent": "FantasyEntries/1.0 (+https://github.com/arth2958/fantasy-live-standings)",
        "Cache-Control": "no-cache", "Pragma": "no-cache"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")

def parse_rosters(html):
    body = html[html.find("<tbody"):]
    teams, in_alternates = [], False
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

def price_pool(teams, rating_of):
    """Compute prices for the pool; rating_of(handle, live_rating) -> rating."""
    n = len(teams)
    center = (n - 1) / 2
    boards = []
    for b in range(8):
        pool = [(h, rating_of(h, live)) for _, ps in teams for h, live in [ps[b]]]
        players = []
        for i, (handle, rtg) in enumerate(pool):
            expected = sum(1 / (1 + 10 ** ((o_rtg - rtg) / 400))
                           for j, (_, o_rtg) in enumerate(pool) if j != i)
            price = max(MIN_PRICE, math.ceil(BASE_PRICE - (center - expected) * STEP))
            players.append({"handle": handle, "rating": rtg, "price": price})
        players.sort(key=lambda p: (-p["rating"], p["handle"].lower()))
        boards.append({"board": b + 1, "players": players})
    return center, boards

def write_prices(teams, center, boards, ratings_locked_at, note):
    data = {
        "season": SEASON, "source": ROSTERS,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "ratings_locked_at": ratings_locked_at,
        "team_count": len(teams), "center": center, "provisional": False,
        "note": note, "boards": boards,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, indent=1) + "\n")

def freeze():
    html = fetch(ROSTERS)
    teams = parse_rosters(html)
    center, boards = price_pool(teams, lambda h, live: live)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    snap = {h.lower(): {"handle": h, "rating": r}
            for _, ps in teams for h, r in ps}
    SNAPSHOT.write_text(json.dumps({"taken_at": now, "ratings": snap}, indent=1) + "\n")
    write_prices(teams, center, boards, now,
                 "Prices locked to this one-time snapshot; do not regenerate.")
    print(f"Frozen: {len(teams)} teams, center {center}, snapshot {SNAPSHOT}")

def watch():
    if not OUT.exists():
        raise SystemExit("No prices JSON yet - run with --freeze first")
    current = json.loads(OUT.read_text())
    if not SNAPSHOT.exists():
        # one-time migration: build the pinned store from the locked JSON
        taken = current.get("ratings_locked_at") or current["generated_at"]
        snap = {p["handle"].lower(): {"handle": p["handle"], "rating": p["rating"]}
                for b in current["boards"] for p in b["players"]}
        SNAPSHOT.write_text(json.dumps({"taken_at": taken, "ratings": snap}, indent=1) + "\n")
        print(f"Migrated snapshot store from locked JSON ({len(snap)} players, taken {taken})")
    snapshot = json.loads(SNAPSHOT.read_text())["ratings"]
    locked_at = json.loads(SNAPSHOT.read_text())["taken_at"]

    html = fetch(ROSTERS)
    teams = parse_rosters(html)
    old_handles = {b["board"]: {p["handle"].lower() for p in b["players"]}
                   for b in current["boards"]}
    new_handles = {}
    for b in range(8):
        new_handles[b + 1] = {ps[b][0].lower() for _, ps in teams}
    diffs = []
    for b in range(1, 9):
        added = sorted(new_handles[b] - old_handles.get(b, set()))
        removed = sorted(old_handles.get(b, set()) - new_handles[b])
        for h in added:
            diffs.append(f"Board {b}: +{h}")
        for h in removed:
            diffs.append(f"Board {b}: -{h}")
    if not diffs and len(teams) == current["team_count"]:
        print(f"No composition change ({len(teams)} teams); prices untouched")
        DIFF.write_text("")
        return

    def rating_of(handle, live):
        pinned = snapshot.get(handle.lower())
        return pinned["rating"] if pinned else live

    center, boards = price_pool(teams, rating_of)
    note = ("Ratings pinned to the snapshot; prices recomputed because roster "
            "composition changed: " + "; ".join(diffs))
    write_prices(teams, center, boards, locked_at, note)
    subject = f"Reprice S50: {len(diffs)} roster change(s), {len(teams)} teams, center {center}"
    body = "\n".join(diffs + ["", f"Existing players keep snapshot ratings from {locked_at}.",
                                "Newcomers priced at live rating at join time."])
    DIFF.write_text(subject + "\n\n" + body + "\n")
    print(subject)
    print(body)

if __name__ == "__main__":
    if "--freeze" in sys.argv:
        freeze()
    else:
        watch()
