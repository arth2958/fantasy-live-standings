#!/usr/bin/env python3
"""Exit 1 (+ print new entries) when S50Entries gains real (non-bot) rows
not yet recorded in .seen-entries. Exit 0 when nothing new."""
import importlib.util, io, json, sys, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("u", ROOT / "scripts" / "update_s50.py")
u = importlib.util.module_from_spec(spec); spec.loader.exec_module(u)

import time
url = u.ENTRIES + "&cb=%d" % time.time()
try:
    with urllib.request.urlopen(url, timeout=20) as r:
        text = r.read().decode()
except Exception as e:
    print("fetch failed:", e); sys.exit(0)  # transient; try next cycle

entries = u.parse_entries(text)
state = ROOT / ".seen-entries"
seen = set(state.read_text().split()) if state.exists() else set()
new = [e for e in entries if e["owner"].casefold() not in seen]
if new:
    for e in new:
        print(json.dumps({"owner": e["owner"], "name": e["name"], "total": e["total"], "picks": e["handles"]}))
    sys.exit(1)
print("no new entries (%d known)" % len(entries))
sys.exit(0)
