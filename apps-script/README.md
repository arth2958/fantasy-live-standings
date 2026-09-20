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

Closing entries (commissioner switch):
- Create a tab named **Settings** in the spreadsheet.
- A1: `SUBMISSIONS`   B1: `OPEN`
- To close entries, set B1 to `CLOSED`. Submissions are then rejected with
  "Entries are closed." and the entries page shows the closed state on load
  (it reads the switch live via the script's doGet).
- Missing Settings tab or cell = OPEN, so nothing breaks before you create it.

Updating the code later: Apps Script web apps do NOT pick up code edits
automatically. After any change: Deploy -> Manage deployments -> pencil icon
-> Version: New version -> Deploy. The URL stays the same.

Notes:
- The page posts with `no-cors` (Apps Script sends no CORS headers), so the
  page cannot read the response. It tells the user to confirm their row in the
  `S50 Entries` tab instead of claiming success it cannot see.
- Resubmissions: `REPLACE_EXISTING = false` blocks a second entry from the same
  owner (case-insensitive). Flip to `true` to replace the old row instead.
- Server-side validation re-checks: exactly 8 picks, one per board, no
  duplicate players, total matches the picks and is within EUR 16,000.
