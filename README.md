# Season 49 fantasy live standings

Static, phone-first standings for the Lichess4545 fantasy league. A scheduled GitHub Action reads the public Season 49 pairings and the public fantasy Entries tab, then refreshes `data/standings.json` every 15 minutes.

Run locally:

```bash
python scripts/update.py
python -m http.server 8000
```
