/* Season switcher + season registry.
   A new season = one entry here plus its data file(s). No page rebuilds.
   - the site root (index.html) reads THIS LIST and forwards visitors to the
     latest season's standings automatically - no separate redirect edit
   - standings pages live in s<N>/ folders (s49/ is the first archive)
   - entries page:   entries/index.html, reads data/prices-s<N>.json */
// *** NEXT SEASON: add one line at the TOP of this list, e.g.
//   { n: 51, entries: "entries/", standings: "s51/" },
// ...and change the old season's "entries" to null once its entries close.
const FANTASY_SEASONS = [
  { n: 50, entries: "entries/", standings: "s50/" },
  { n: 49, entries: null, standings: "s49/" },
];

function initSeasonSwitcher() {
  const body = document.body;
  const current = Number(body.dataset.season);
  const root = body.dataset.root || "";
  const header = document.querySelector("header");
  if (!header || !current) return;
  const wrap = document.createElement("div");
  wrap.className = "season-switch";
  const label = document.createElement("span");
  label.textContent = "Season";
  const sel = document.createElement("select");
  sel.setAttribute("aria-label", "Choose season");
  for (const s of FANTASY_SEASONS.slice().sort((a, b) => b.n - a.n)) {
    const opt = document.createElement("option");
    opt.value = s.n;
    opt.textContent = `Season ${s.n}`;
    if (s.n === current) opt.selected = true;
    sel.appendChild(opt);
  }
  sel.addEventListener("change", () => {
    const target = FANTASY_SEASONS.find(s => s.n === Number(sel.value));
    if (!target) return;
    const kind = body.dataset.page; // "standings" or "entries"
    let path = target[kind];
    if (path == null) path = target.entries ?? target.standings; // fall back to what exists
    if (path != null) location.href = root + path;
  });
  wrap.append(label, sel);
  const h1 = header.querySelector("h1");
  header.insertBefore(wrap, h1 || header.firstChild);
}
document.addEventListener("DOMContentLoaded", initSeasonSwitcher);
