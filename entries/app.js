/* Season 50 fantasy entry form. */
const SEASON = Number(document.body.dataset.season || 50);
const APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbxIVFQQFFKTAmkjt03wSI5yxg5tSyCsLf1AiPyN3iAb7_DtCbjWLXvWLPwmaaOFcLVJeA/exec"; // <-- paste the deployed Apps Script web-app URL here
const BUDGET = 16000, BOARDS = 8;
const q = s => document.querySelector(s), euro = n => n.toLocaleString("en-US");
let data = null;
const picks = new Array(BOARDS).fill(null);

async function load() {
  try {
    const r = await fetch(`../data/prices-s${SEASON}.json?` + Date.now(), { cache: "no-store" });
    data = await r.json();
    const when = new Date(data.generated_at);
    const lockedAt = data.ratings_locked_at ? new Date(data.ratings_locked_at) : when;
    q("#status").textContent = data.provisional
      ? `Prices from the live roster, updated ${when.toLocaleString([], { dateStyle: "medium", timeStyle: "short" })}`
      : `Ratings frozen at the ${lockedAt.toLocaleString([], { dateStyle: "medium", timeStyle: "short" })} snapshot`;
    q("#provenance").textContent = `${data.team_count} teams x 8 boards from lichess4545. ` +
      (data.provisional
        ? "Rosters are still open - prices refresh until registration closes."
        : `Player ratings are pinned to the ${lockedAt.toLocaleString([], { dateStyle: "medium", timeStyle: "short" })} snapshot. If a team drops out or joins before entries close, any repricing is decided and announced by the league - never changed silently.`);
    renderBoards();
  } catch (e) {
    q("#status").textContent = "Could not load player prices. Reload to try again.";
  }
}

function renderBoards() {
  const host = q("#boards");
  host.innerHTML = "";
  for (const board of data.boards) {
    const node = q("#boardtpl").content.cloneNode(true);
    const article = node.querySelector(".board");
    article.dataset.board = board.board;
    node.querySelector("h3").textContent = `Board ${board.board}`;
    const input = node.querySelector("input");
    const options = node.querySelector(".options");
    const show = term => {
      const needle = term.trim().toLowerCase();
      const list = board.players.filter(p => !needle || p.handle.toLowerCase().includes(needle));
      options.innerHTML = "";
      if (!list.length) { options.innerHTML = '<div class="opt empty">No match on this board.</div>'; }
      for (const p of list) {
        const o = document.createElement("button");
        o.type = "button"; o.className = "opt";
        o.innerHTML = `<span class="h"></span><span class="r"></span><span class="p"></span>`;
        o.querySelector(".h").textContent = p.handle;
        o.querySelector(".r").textContent = p.rating;
        o.querySelector(".p").textContent = euro(p.price);
        o.onclick = () => select(board.board, p, article);
        options.appendChild(o);
      }
      options.hidden = false;
    };
    input.addEventListener("focus", () => show(input.value));
    input.addEventListener("input", () => show(input.value));
    input.addEventListener("blur", () => setTimeout(() => { options.hidden = true; }, 150));
    node.querySelector(".clear").onclick = () => select(board.board, null, article);
    host.appendChild(node);
  }
}

function select(boardNo, player, article) {
  picks[boardNo - 1] = player ? { board: boardNo, ...player } : null;
  const pickEl = article.querySelector(".pick"), chooser = article.querySelector(".chooser");
  if (player) {
    pickEl.hidden = false; chooser.style.display = "none";
    pickEl.querySelector(".who").textContent = `${player.handle} (${player.rating})`;
    pickEl.querySelector(".cost").textContent = euro(player.price);
    article.classList.add("chosen");
  } else {
    pickEl.hidden = true; chooser.style.display = "";
    const input = chooser.querySelector("input"); input.value = ""; input.focus();
    article.classList.remove("chosen");
  }
  updateBar();
}

const chosen = () => picks.filter(Boolean);
const total = () => chosen().reduce((s, p) => s + p.price, 0);

function updateBar() {
  const n = chosen().length, t = total(), left = BUDGET - t;
  q("#picked").textContent = `${n}/${BOARDS}`;
  q("#spent").textContent = euro(t);
  q("#left").textContent = euro(left);
  q("#bartotal").textContent = euro(t);
  const bar = q("#submitbar"), btn = q("#submit");
  bar.classList.toggle("over", left < 0);
  q("#left").parentElement.classList.toggle("over", left < 0);
  if (n < BOARDS) { btn.disabled = true; btn.textContent = `Pick ${BOARDS - n} more player${BOARDS - n > 1 ? "s" : ""}`; }
  else if (left < 0) { btn.disabled = true; btn.textContent = `${euro(-left)} over budget`; }
  else { btn.disabled = false; btn.textContent = "Submit entry"; }
}

function validate() {
  const owner = q("#owner").value.trim();
  if (chosen().length !== BOARDS) return "Pick one player from each of the 8 boards.";
  if (total() > BUDGET) return `Over budget by ${euro(total() - BUDGET)}.`;
  if (!owner) return "Add your name so the league knows whose team this is.";
  const handles = chosen().map(p => p.handle.toLowerCase());
  if (new Set(handles).size !== handles.length) return "The same player cannot be picked twice.";
  return null;
}

function entry() {
  return {
    season: SEASON, owner: q("#owner").value.trim(), team: q("#teamname").value.trim() || (q("#owner").value.trim() + "’s team"),
    picks: chosen().map(p => ({ board: p.board, handle: p.handle, rating: p.rating, price: p.price })),
    total: total(), prices_generated_at: data.generated_at,
  };
}

function queueLocal(e, reason) {
  const k = "s50-pending";
  const list = JSON.parse(localStorage.getItem(k) || "[]");
  list.push({ ...e, queued_at: new Date().toISOString(), reason });
  localStorage.setItem(k, JSON.stringify(list));
  renderQueue();
}

function renderQueue() {
  const list = JSON.parse(localStorage.getItem("s50-pending") || "[]");
  const host = q("#queued"), note = q("#queue-note");
  host.innerHTML = "";
  if (!list.length) { note.hidden = true; return; }
  note.hidden = false;
  note.textContent = "Entries below are saved on this device only - they have NOT reached the league sheet yet.";
  for (const e of list) {
    const d = document.createElement("div");
    d.className = "queued";
    d.textContent = `${e.owner} - ${e.picks.length} players, ${euro(e.total)} (${e.reason})`;
    host.appendChild(d);
  }
}

async function submit() {
  const err = validate();
  if (err) { alert(err); return; }
  const e = entry(), btn = q("#submit");
  btn.disabled = true; btn.textContent = "Submitting…";
  if (!APPS_SCRIPT_URL) {
    queueLocal(e, "endpoint not connected");
    btn.textContent = "Saved on this device";
    alert("The submission endpoint is not connected yet. Your entry is saved on this device and listed at the bottom of the page. Nothing was sent to the league sheet.");
    updateBar(); return;
  }
  try {
    await fetch(APPS_SCRIPT_URL, {
      method: "POST", mode: "no-cors",
      headers: { "Content-Type": "text/plain" },
      body: JSON.stringify(e),
    });
    btn.textContent = "Sent";
    alert("Entry sent - thanks! Your team will appear on the standings page within about 20 minutes (the site refreshes every 15 minutes plus a short deploy).");
  } catch (ex) {
    queueLocal(e, "send failed");
    btn.textContent = "Saved on this device";
    alert("Sending failed, so your entry was saved on this device instead. It is listed at the bottom of the page. Nothing reached the league sheet.");
  }
  updateBar();
}

q("#submit").onclick = submit;

function checkStatus() {
  if (!APPS_SCRIPT_URL) return;
  const cb = "s50status" + Date.now();
  window[cb] = res => {
    delete window[cb];
    if (res && res.submissions === "CLOSED") setClosed();
  };
  const s = document.createElement("script");
  s.src = APPS_SCRIPT_URL + (APPS_SCRIPT_URL.includes("?") ? "&" : "?") + "callback=" + cb;
  s.onload = () => s.remove();
  s.onerror = () => s.remove(); // status unknown: sheet stays source of truth
  document.body.appendChild(s);
}

function setClosed() {
  const btn = q("#submit");
  btn.disabled = true;
  btn.textContent = "Entries are closed";
  q("#status").textContent = "Entries are closed.";
  document.querySelectorAll(".board input, .board .clear, #owner, #teamname")
    .forEach(el => { el.disabled = true; });
}

load(); renderQueue(); checkStatus();
