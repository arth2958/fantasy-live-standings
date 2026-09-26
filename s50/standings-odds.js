// Dev only: frozen game-start Elo expectations, kept separate from scoring.
(async () => {
  const table = document.querySelector('#table');
  const popular = document.querySelector('#popular');
  if (!table || !popular) return;
  let data;
  try {
    const response = await fetch('../data/league-s50.json?' + Date.now(), {cache: 'no-store'});
    if (!response.ok) return;
    data = await response.json();
  } catch (_) { return; }
  const byHandle = new Map();
  Object.values(data.teams || {}).forEach(team => (team.players || []).forEach(player => {
    byHandle.set(String(player.handle).toLowerCase(), player);
  }));
  const annotate = () => {
    popular.querySelectorAll('.popcell').forEach(card => {
      if (card.dataset.pregameShown) return;
      const handle = card.querySelector('b')?.querySelector('a:not(.league-profile)')?.textContent?.trim()
        || card.querySelector('b')?.childNodes[0]?.textContent?.trim();
      const player = byHandle.get((handle || '').toLowerCase());
      if (!player || player.pregame_expectation == null) return;
      const note = document.createElement('small');
      note.className = 'pregame-note';
      note.style.cssText = 'display:block;font-size:11px;font-weight:700;margin-top:4px';
      note.textContent = `Pre-game Elo ${Math.round(player.pregame_expectation * 100)}%`;
      card.append(note);
      card.dataset.pregameShown = 'true';
    });
    table.querySelectorAll('.roster .player').forEach(row => {
      const name = row.querySelector('span:first-child');
      if (!name || row.dataset.pregameShown) return;
      const handle = name.querySelector('a:not(.league-profile)')?.textContent?.trim()
        || name.textContent.replace('↗', '').trim();
      const player = byHandle.get(handle.toLowerCase());
      if (!player) return;
      if (player.pregame_expectation == null) return;
      const note = document.createElement('small');
      note.className = 'pregame-note';
      note.textContent = `Pre-game Elo ${Math.round(player.pregame_expectation * 100)}%`;
      row.append(note);
      row.dataset.pregameShown = 'true';
    });
  };
  annotate();
  new MutationObserver(annotate).observe(table, {childList: true, subtree: true});
  new MutationObserver(annotate).observe(popular, {childList: true, subtree: true});
})();
