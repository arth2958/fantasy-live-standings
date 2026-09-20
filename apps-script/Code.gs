/**
 * Season 50 fantasy entries collector.
 *
 * Deploy: see apps-script/README.md. Receives POSTs from the entries page and
 * appends validated rows to an "S50 Entries" tab in this spreadsheet.
 */
const SHEET_NAME = 'S50 Entries';
const BUDGET_CAP = 16000;
const BOARDS = 8;
const REPLACE_EXISTING = false; // set true to let an owner resubmit (replaces the old row)

// Commissioner's close switch: a "Settings" tab in this spreadsheet,
// A1 = SUBMISSIONS, B1 = OPEN or CLOSED. Checked on every submission.
// Missing tab/cell defaults to OPEN.
const SETTINGS_SHEET = 'Settings';
const STATUS_CELL = 'B1';

function doPost(e) {
  try {
    if (readStatus() === 'CLOSED') return json({ ok: false, error: 'Entries are closed.' });
    const data = JSON.parse(e.postData.contents);
    const err = validate(data);
    if (err) return json({ ok: false, error: err });
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    let sheet = ss.getSheetByName(SHEET_NAME);
    if (!sheet) {
      sheet = ss.insertSheet(SHEET_NAME);
      sheet.appendRow(header());
    }
    const owner = String(data.owner).trim();
    const rows = sheet.getDataRange().getValues();
    const ownerCol = columnOf(rows[0], ['owner'], 0);
    for (let i = 1; i < rows.length; i++) {
      if (String(rows[i][ownerCol]).trim().toLowerCase() === owner.toLowerCase()) {
        if (!REPLACE_EXISTING) return json({ ok: false, error: 'An entry for this owner already exists.' });
        sheet.deleteRow(i + 1);
        break;
      }
    }
    const picks = data.picks.slice().sort((a, b) => a.board - b.board);
    const hdr = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
    const row = new Array(hdr.length).fill('');
    row[columnOf(hdr, ['timestamp', 'date submitted'], 0)] = new Date();
    row[columnOf(hdr, ['owner'], 0)] = owner;
    const ni = columnOf(hdr, ['team name', 'fantasy team'], -1);
    if (ni >= 0) row[ni] = String(data.team || '').trim();
    for (const p of picks) {
      const i = columnOf(hdr, ['board ' + p.board], -1);
      if (i >= 0) row[i] = p.handle;
    }
    // dead boards (9 and 10 in the old layout) get n/a, matching prior seasons
    for (let b = BOARDS + 1; b <= 10; b++) {
      const i = columnOf(hdr, ['board ' + b], -1);
      if (i >= 0) row[i] = 'n/a';
    }
    const ti = columnOf(hdr, ['total', 'total price'], -1);
    if (ti >= 0) row[ti] = data.total;
    sheet.appendRow(row);
    return json({ ok: true });
  } catch (err) {
    return json({ ok: false, error: String(err) });
  }
}

function validate(d) {
  if (!d || typeof d !== 'object') return 'Empty submission.';
  if (!String(d.owner || '').trim()) return 'Missing owner name.';
  if (!Array.isArray(d.picks) || d.picks.length !== BOARDS) return 'Entry must have exactly 8 players.';
  const boards = d.picks.map(p => p && p.board);
  for (let b = 1; b <= BOARDS; b++) if (boards.indexOf(b) === -1) return 'Missing a pick for board ' + b + '.';
  const handles = d.picks.map(p => String(p.handle || '').trim().toLowerCase());
  if (handles.some(h => !h)) return 'A pick is missing a player name.';
  if (new Set(handles).size !== handles.length) return 'The same player cannot be picked twice.';
  let sum = 0;
  for (const p of d.picks) {
    const price = Number(p.price);
    if (!isFinite(price) || price < 0) return 'A pick has an invalid price.';
    sum += price;
  }
  if (sum !== Number(d.total)) return 'Total does not match the picks.';
  if (sum > BUDGET_CAP) return 'Over the ' + BUDGET_CAP + ' budget.';
  return null;
}

// Status endpoint for the entries page. Supports JSONP (?callback=fn) because
// Apps Script sends no CORS headers, so the page reads this via a script tag.
function doGet(e) {
  const payload = JSON.stringify({ season: 50, submissions: readStatus() });
  const cb = e && e.parameter && e.parameter.callback;
  if (cb && /^[A-Za-z_$][\w$]*$/.test(cb)) {
    return ContentService.createTextOutput(cb + '(' + payload + ');')
      .setMimeType(ContentService.MimeType.JAVASCRIPT);
  }
  return ContentService.createTextOutput(payload)
    .setMimeType(ContentService.MimeType.JSON);
}

function readStatus() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(SETTINGS_SHEET);
  if (!sheet) return 'OPEN';
  const v = String(sheet.getRange(STATUS_CELL).getValue() || '').trim().toUpperCase();
  return v === 'CLOSED' ? 'CLOSED' : 'OPEN';
}

function columnOf(headerRow, names, fallback) {
  const lowered = headerRow.map(h => String(h).trim().toLowerCase());
  for (const n of names) {
    const i = lowered.indexOf(n);
    if (i >= 0) return i;
  }
  return fallback;
}

function header() {
  const cols = ['Timestamp', 'Owner', 'Team name'];
  for (let b = 1; b <= BOARDS; b++) cols.push('Board ' + b);
  cols.push('Total');
  return cols;
}

function json(o) {
  return ContentService.createTextOutput(JSON.stringify(o))
    .setMimeType(ContentService.MimeType.JSON);
}
