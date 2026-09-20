/* Season switcher + season registry.
   A new season = one entry here plus its data file(s). No page rebuilds.
   - standings page: root index.html, reads data/standings.json (S49 archive)
   - entries page:   entries/index.html, reads data/prices-s<N>.json */
const FANTASY_SEASONS = [
  { n: 50, entries: "entries/", standings: null }, // standings added when S50 play begins
  { n: 49, entries: null, standings: "" },
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
  const eyebrow = header.querySelector(".eyebrow");
  header.insertBefore(wrap, eyebrow ? eyebrow.nextSibling : header.firstChild);
}
document.addEventListener("DOMContentLoaded", initSeasonSwitcher);
