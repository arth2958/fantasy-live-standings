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
      const label = row.querySelector('small');
      const handle = row.querySelector('b a')?.textContent?.trim();
      if (!label || !handle || label.dataset.pregameShown) return;
      const player = byHandle.get(handle.toLowerCase());
      if (!player) return;
      if (player.pregame_expectation == null) return;
      const note = `pre-game Elo ${Math.round(player.pregame_expectation * 100)}%`;
      label.append(document.createTextNode(` · ${note}`));
      label.dataset.pregameShown = 'true';
    });
  };
  annotate();
  new MutationObserver(annotate).observe(table, {childList: true, subtree: true});
})();
