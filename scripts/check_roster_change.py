#!/usr/bin/env python3
"""Check S50 roster composition against the locked snapshot.

Exit 0 if unchanged, exit 1 and print the exact diffs if any team was
dropped, added, or replaced. Ignores rating drift entirely. Never reprices.
"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_prices import fetch, parse_rosters, ROSTERS, OUT

def main():
    current = json.loads(OUT.read_text())
    teams = parse_rosters(fetch(ROSTERS))
    diffs = []
    if len(teams) != current["team_count"]:
        diffs.append(f"team count {current['team_count']} -> {len(teams)}")
    for b in range(1, 9):
        old = {p["handle"].lower() for p in current["boards"][b - 1]["players"]}
        new = {ps[b - 1][0].lower() for _, ps in teams}
        for h in sorted(new - old):
            diffs.append(f"Board {b}: +{h}")
        for h in sorted(old - new):
            diffs.append(f"Board {b}: -{h}")
    if diffs:
        print("ROSTER CHANGED since locked snapshot:")
        print("\n".join(diffs))
        sys.exit(1)
    print(f"No composition change ({len(teams)} teams)")
    sys.exit(0)

if __name__ == "__main__":
    main()
