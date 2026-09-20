# Season 49 fantasy live standings

Static, phone-first standings for the Lichess4545 fantasy league. A scheduled GitHub Action reads the public Season 49 pairings and the public fantasy Entries tab, then refreshes `data/standings.json` every 15 minutes.

Run locally:

```bash
python scripts/update.py
python -m http.server 8000
```

## Starting a new season

See **SEASON-FLIP.md** - a plain-language, no-coding-needed checklist for
rolling the sheet, the Apps Script, and this site to the next season.

## Season 50 entries app

`entries/` is the Season 50 fantasy entry form: pick one player per board (8
players) within 16,000. Prices come from `data/prices-s50.json`. Player ratings are pinned to a
one-time snapshot (`data/ratings-s50-snapshot.json`, taken 2026-09-20 11:27
UTC). The "Update S50 prices" workflow runs every ~15 minutes but only
reprices when roster composition changes (a team drops out or joins before
entries close): existing players keep snapshot ratings, newcomers are priced
at their live rating, center recalculates as (N-1)/2. Rating drift on lichess
is ignored. Each reprice commit message lists what changed.

Submissions go to a Google Apps Script web app that appends to the league
spreadsheet - see `apps-script/README.md` for deployment.
