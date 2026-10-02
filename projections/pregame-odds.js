// Dev preview: annotate finished and pending games with the ratings from game start.
(async () => {
  const table = document.querySelector('#combined-table');
  if (!table) return;
  let data;
  try {
    const response = await fetch(`../data/league-s50.json?${Date.now()}`, {cache: 'no-store'});
    if (!response.ok) return;
    data = await response.json();
  } catch (_) { return; }
  const byHandle = new Map();
  Object.values(data.teams || {}).forEach(team => (team.players || []).forEach(player => {
    byHandle.set(String(player.handle).toLowerCase(), player);
  }));
  const annotate = () => {
    table.querySelectorAll('.projection-roster > span').forEach(row => {
      // ELO DETAIL: its own darker line, separate from the lighter score and status.
      // Plain-text names also need estimates before a current-round game link exists.
      const name = row.querySelector('b');
      const handle = name?.querySelector('a:not(.league-profile)')?.textContent?.trim()
        || name?.textContent.replace('↗', '').trim();
      if (!handle || row.dataset.pregameShown) return;
      const player = byHandle.get(handle.toLowerCase());
      if (!player) return;
      if (player.pregame_expectation == null && player.live_elo_estimate == null) return;
      const note = document.createElement('small');
      note.className = 'elo-detail';
      note.textContent = player.pregame_expectation != null
        ? `Pre-game Elo ${Math.round(player.pregame_expectation * 100)}%`
        : `Elo estimate ${Math.round(player.live_elo_estimate * 100)}%`;
      row.append(note);
      row.dataset.pregameShown = 'true';
    });
  };
  annotate();
  new MutationObserver(annotate).observe(table, {childList: true, subtree: true});
})();
