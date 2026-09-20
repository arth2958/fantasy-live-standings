# Deploying the entries endpoint (5 minutes)

The entries page POSTs submissions to a Google Apps Script web app attached to
the league spreadsheet. Until this is deployed, the page saves entries locally
on the device and says so - nothing reaches the sheet.

1. Open the league spreadsheet in Google Sheets.
2. Extensions -> Apps Script.
3. Delete any starter code, paste the full contents of `Code.gs`, save.
4. Deploy -> New deployment -> type: **Web app**.
   - Execute as: **Me**
   - Who has access: **Anyone** (the public form needs this; the script only
     appends rows to the `S50 Entries` tab it creates)
5. Copy the web app URL (`https://script.google.com/macros/s/.../exec`).
6. Paste it into `entries/app.js` as the `APPS_SCRIPT_URL` constant and push,
   or tell me the URL and I'll wire it up.

Notes:
- The page posts with `no-cors` (Apps Script sends no CORS headers), so the
  page cannot read the response. It tells the user to confirm their row in the
  `S50 Entries` tab instead of claiming success it cannot see.
- Resubmissions: `REPLACE_EXISTING = false` blocks a second entry from the same
  owner (case-insensitive). Flip to `true` to replace the old row instead.
- Server-side validation re-checks: exactly 8 picks, one per board, no
  duplicate players, total matches the picks and is within EUR 16,000.
