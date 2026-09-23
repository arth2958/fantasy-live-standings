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
  { n: 48, entries: null, standings: "s48/" },
  { n: 47, entries: null, standings: "s47/" },
  { n: 46, entries: null, standings: "s46/" },
  { n: 45, entries: null, standings: "s45/" },
  { n: 44, entries: null, standings: "s44/" },
  { n: 43, entries: null, standings: "s43/" },
  { n: 42, entries: null, standings: "s42/" },
  { n: 41, entries: null, standings: "s41/" },
  { n: 40, entries: null, standings: "s40/" },
  { n: 39, entries: null, standings: "s39/" },
  { n: 38, entries: null, standings: "s38/" },
  { n: 37, entries: null, standings: "s37/" },
  { n: 36, entries: null, standings: "s36/" },
  { n: 35, entries: null, standings: "s35/" },
  { n: 34, entries: null, standings: "s34/" },
  { n: 33, entries: null, standings: "s33/" },
  { n: 32, entries: null, standings: "s32/" },
  { n: 31, entries: null, standings: "s31/" },
  { n: 30, entries: null, standings: "s30/" },
  { n: 29, entries: null, standings: "s29/" },
  { n: 28, entries: null, standings: "s28/" },
  { n: 27, entries: null, standings: "s27/" },
  { n: 26, entries: null, standings: "s26/" },
  { n: 25, entries: null, standings: "s25/" },
  { n: 24, entries: null, standings: "s24/" },
  { n: 23, entries: null, standings: "s23/" },
  { n: 22, entries: null, standings: "s22/" },
  { n: 21, entries: null, standings: "s21/" },
  { n: 20, entries: null, standings: "s20/" },
  { n: 19, entries: null, standings: "s19/" },
  { n: 18, entries: null, standings: "s18/" },
  { n: 17, entries: null, standings: "s17/" },
  { n: 16, entries: null, standings: "s16/" },
  { n: 15, entries: null, standings: "s15/" },
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
