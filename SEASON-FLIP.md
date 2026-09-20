# Starting a new fantasy season - plain-language guide

No coding or GitHub experience needed. Every step is either clicking in a
browser or changing one obvious number. Where a file must be edited, the exact
spot is marked with a comment that says `UPDATE EACH SEASON`.

The five moving pieces:

1. **The Google Sheet** ("Fantasy league NEW") - stores entries and prices.
2. **The Apps Script** - the little program that receives form submissions and
   writes them into the sheet.
3. **This GitHub repo** - the website's files.
4. **GitHub Actions** - the robot that rebuilds the standings every 15 minutes.
5. **GitHub Pages** - just serves whatever is in the repo. No setup needed.

Below, `<NN>` means the new season number (for example 51).

---

## Step 1 - The Google Sheet (about 5 minutes)

Open the league spreadsheet.

1. Right-click the `S50Entries` tab at the bottom -> **Duplicate**. Rename the
   copy to `S<NN>Entries` (example: `S51Entries`). Delete any old rows so only
   the header row remains.
2. Fill the **Prices** tab with the new season's roster and prices, keeping
   the same layout (Team column, then Handle / blank / Rtg / Price blocks for
   Boards 1-8). The entry form validates picks against this tab.
3. The **Settings** tab needs no change - it stays `SUBMISSIONS / OPEN` and
   works every season. Set B1 to `CLOSED` whenever entries should stop.

## Step 2 - The Apps Script (about 5 minutes)

1. In the spreadsheet: **Extensions -> Apps Script**.
2. Open `Code.gs`. Change the two lines marked `UPDATE EACH SEASON`:
   - `SHEET_NAME = 'S50Entries'` becomes `'S<NN>Entries'`
   - `season: 50` becomes the new number (in the `doGet` function)
3. Save (disk icon).
4. **Deploy -> Manage deployments -> pencil icon -> Version: New version ->
   Deploy.** The web address stays the same. Skipping this step means the old
   season's code keeps running.

## Step 3 - The website files on GitHub (about 15 minutes)

Do this on github.com in the repository - each file has a pencil (Edit this
file) button; change the text, then **Commit changes** at the bottom.

1. `seasons.js` - add one line at the top of the list (there is a comment
   showing exactly what to paste), and set the old season's `entries:` to
   `null`. This one line also makes the site's front page
   (`https://arth2958.github.io/fantasy-live-standings/`) forward visitors to
   the new season automatically - the front page just reads the list.
2. Standings page: open the `s50` folder, copy `index.html` and `app.js` into
   a new folder named `s<NN>` (each season keeps its own folder - `s49/` is
   the first archive, `s50/` the current one). In the copies, change `data-season="50"` and
   every "Season 50" text to the new number. (On github.com: open each file,
   copy its contents, then **Add file -> Create new file**, type
   `s<NN>/index.html` as the name, paste, commit.)
3. Entries page: edit `entries/index.html` - change `data-season="50"` and the
   "Season 50" texts.
4. Prices data: this is the one step that runs a program. On any computer with
   Python: change `SEASON = 50` in `scripts/build_prices.py` to the new number
   and run `python scripts/build_prices.py` once, right after the season's
   rosters are published. That creates `data/prices-s<NN>.json` and the
   ratings snapshot. Upload both new files to the repo's `data` folder
   (**Add file -> Upload files**).
   (Easier alternative: ask Instinct to run it - it has done this before.)
5. Standings builder: in `scripts/`, copy `update_s50.py` to
   `update_s<NN>.py` and change the four marked lines at the top (season
   number, entries tab name, two filenames).

## Step 4 - The standings robot (GitHub Actions, 2 minutes)

Edit `.github/workflows/update.yml`:

1. Under the existing `- run: python scripts/update_s50.py` line, add
   `- run: python scripts/update_s<NN>.py`.
2. In the `git add` line, add `data/standings-s<NN>.json`.

Commit. The robot now refreshes the new season every 15 minutes.

## Step 5 - Check it works

- Visit the standings page: `https://arth2958.github.io/fantasy-live-standings/s<NN>/`
- Visit the entry form: `https://arth2958.github.io/fantasy-live-standings/entries/`
- Submit a test entry and confirm it appears in the sheet's `S<NN>Entries`
  tab, then delete the test row.
- Note: GitHub Pages caches pages for about 10 minutes, so a hard refresh
  (Ctrl+Shift+R) may be needed to see changes.

## What NOT to touch

- `style.css`, `app.js` files other than the season number/text spots -
  layout and logic are season-independent.
- The Apps Script `Settings` tab names, budget cap (16,000), and board count
  (8) - league constants.
- Old season folders and files - they are the archive.

## If stuck

Every spot that needs a seasonal change is marked in the code with
`UPDATE EACH SEASON` or `NEXT SEASON`. Searching the repo for those two
phrases lists them all. And you can always hand this file to Instinct - it
has done this flip before and can do the whole thing.
