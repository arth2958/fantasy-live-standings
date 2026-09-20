# Season 49 fantasy live standings

Static, phone-first standings for the Lichess4545 fantasy league. A scheduled GitHub Action reads the public Season 49 pairings and the public fantasy Entries tab, then refreshes `data/standings.json` every 15 minutes.

Run locally:

```bash
python scripts/update.py
python -m http.server 8000
```

## Season 50 entries app

`entries/` is the Season 50 fantasy entry form: pick one player per board (8
players) within EUR 16,000. Prices come from `data/prices-s50.json`, generated
by `scripts/build_prices.py` from the live Season 50 roster page and refreshed
by the "Update S50 prices" workflow every ~15 minutes until registration
closes (freeze the final JSON at close by disabling that workflow).

Submissions go to a Google Apps Script web app that appends to the league
spreadsheet - see `apps-script/README.md` for deployment.
