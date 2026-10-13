/* ROUND HISTORY, shared by standings and projections.
 * Round totals are actual only. Historical Elo is separate game-start context.
 * No season number here. Each page supplies its own published round_scores.
 * To reuse next season, keep this file and its CSS links on both pages.
 */
// Shared page-wide lookup. Both pages use the same historical league game data.
// NEXT SEASON: set body data-season on each page; this URL follows that value.
let historyEloPromise;
function historicalElo() {
  if (!historyEloPromise) {
    const season = document.body.dataset.season;
    historyEloPromise = /^\d+$/.test(season || '') ?
      fetch(`../data/league-s${season}.json`, {cache: 'no-store'}).then(r => {
        if (!r.ok) throw new Error('Historical Elo unavailable');
        return r.json();
      }).then(data => {
        const lookup = new Map();
        const currentPlayers = new Map();
        Object.values(data.teams || {}).forEach(team => (team.players || []).forEach(player => {
          currentPlayers.set(`${player.handle.toLowerCase()}|${player.opponent.toLowerCase()}`, player);
        }));
        Object.values(data.teams || {}).forEach(team => (team.round_scores || []).forEach(round =>
          (round.players || []).forEach(player => (player.games || []).forEach(game => {
            const value = game.pregame_expectation;
            if (!game.no_play && game.game_url && typeof value === 'number' && value >= 0 && value <= 1)
              lookup.set(`${game.game_url}|${player.handle.toLowerCase()}`, value);
          }))));
        return {lookup, currentPlayers, round: data.round};
      }).catch(() => ({lookup: new Map(), currentPlayers: new Map()})) : Promise.resolve({lookup: new Map(), currentPlayers: new Map()});
  }
  return historyEloPromise;
}
window.roundHistory = function(scores, current) {
  const section = document.createElement('section');
  section.className = 'round-scores round-history';
  section.setAttribute('aria-label', 'Round scores and player results');
  if (!scores || !scores.length) return section;
  const heading = document.createElement('h3'); heading.textContent = 'Round scores';
  const grid = document.createElement('div'); grid.className = 'round-score-grid';
  const note = document.createElement('p'); note.className = 'round-score-note';
  note.textContent = 'Actual points only. Tap a round to see player results.';
  const panel = document.createElement('div'); panel.className = 'round-result-panel'; panel.hidden = true;
  const reset = document.createElement('button'); reset.className = 'round-reset';
  reset.textContent = 'Back to current roster'; reset.hidden = true;
  const number = n => String(Number(n));
  const buttons = [];
  const gameURL = u => /^https:\/\/lichess\.org\/[A-Za-z0-9]{8,12}(\/(white|black))?$/.test(String(u || ''));
  function show(round, button) {
    buttons.forEach(b => {b.classList.toggle('selected', b === button); b.setAttribute('aria-pressed', String(b === button));});
    section.parentElement.classList.add('view-history');
    panel.replaceChildren(); panel.hidden = false; reset.hidden = false;
    const title = document.createElement('h4');
    title.textContent = `Round ${round.round} · ${number(round.points)} actual points · ${round.finished}/${round.paired} games finished`;
    panel.append(title);
    const players = document.createElement('div'); players.className = 'round-result-players';
    (round.players || []).forEach(player => {
      const card = document.createElement('div'); card.className = 'history-player';
      const games = player.games || [];
      // Multiple games must remain visible, even when a player fills two boards.
      const decided = games.filter(g => g.actual_result != null);
      const status = !games.length ? 'unpaired' : decided.length < games.length ? 'pending' :
        games.length === 1 ? games[0].status : 'mixed';
      card.classList.add(status);
      const name = document.createElement('b');
      const nameLink = document.createElement('a');
      const linkedGame = games.find(g => gameURL(g.game_url));
      if (linkedGame) {
        nameLink.href = linkedGame.game_url; nameLink.target = '_blank'; nameLink.rel = 'noopener';
        nameLink.textContent = player.handle; name.append(nameLink);
      } else name.textContent = player.handle;
      const profile = document.createElement('a'); profile.className = 'league-profile';
      profile.href = `https://www.lichess4545.com/team4545/season/${document.body.dataset.season}/player/${encodeURIComponent(player.handle)}/`;
      profile.target = '_blank'; profile.rel = 'noopener'; profile.textContent = '↗';
      profile.setAttribute('aria-label', `Open ${player.handle} league profile`); name.append(' ', profile);
      const score = document.createElement('small'); score.className = 'history-score';
      score.textContent = `${number(player.points || 0)} pts / ${decided.length} games`;
      card.append(name);
      // Season totals remain outside this selected-round view; show per-game detail below.
      if (!games.length) {
        const line = document.createElement('small'); line.textContent = 'Not playing this round'; card.append(line);
      }
      games.forEach(game => {
        const line = document.createElement('small'); line.className = 'history-game round-state';
        const word = game.actual_result == null ? (game.game_url ? 'Playing' : 'Pending') :
          ({won: 'Win', draw: 'Draw', lost: 'Loss'}[game.status] || 'Final');
        const text = `${word}${game.no_play ? ' (no play)' : ''}`;
        if (gameURL(game.game_url)) {
          const link = document.createElement('a'); link.href = game.game_url;
          link.target = '_blank'; link.rel = 'noopener'; link.textContent = text;
          link.setAttribute('aria-label', `${player.handle}: ${text}. Open round ${round.round} game`);
          line.append(link);
        } else line.textContent = text;
        card.append(line);
        const detail = document.createElement('small'); detail.className = 'history-detail';
        detail.textContent = game.actual_result == null ? `Pending vs ${game.opponent}` :
          `${Number(game.actual_result).toFixed(2)} final${game.no_play ? ' (no play)' : ''} vs ${game.opponent}`;
        card.append(detail);
        // A no-play or missing snapshot has no estimate. Never infer one from today's ratings.
        if (!game.no_play) historicalElo().then(data => {
          if (!line.isConnected) return;
          // Only the current round may use today's live estimate for an unstarted game.
          // Historical rounds never fall back to live ratings or today's opponent.
          const isCurrent = Number(round.round) === Number(current) && Number(round.round) === Number(data.round);
          const now = isCurrent ? data.currentPlayers.get(`${player.handle.toLowerCase()}|${String(game.opponent).toLowerCase()}`) : null;
          const fixed = data.lookup.get(`${game.game_url}|${player.handle.toLowerCase()}`);
          const pregame = fixed ?? (now && game.actual_result == null ? now.pregame_expectation : null);
          const live = now && game.actual_result == null && pregame == null ? now.live_elo_estimate : null;
          const estimate = pregame ?? live;
          if (estimate == null) return;
          if (game.actual_result == null && now)
            detail.textContent = `${Number(now.expected_points).toFixed(2)} projected vs ${game.opponent}`;
          const elo = document.createElement('small'); elo.className = 'history-elo elo-detail';
          elo.textContent = `${pregame != null ? 'Pre-game Elo' : 'Elo estimate'} ${Math.round(estimate * 100)}%`;
          detail.after(elo);
        });
      });
      players.append(card);
    });
    if (!(round.players || []).length) {
      const empty = document.createElement('p'); empty.textContent = 'Player results are not available in this published snapshot yet.'; panel.append(empty);
    }
    panel.append(players);
  }
  scores.forEach(round => {
    const button = document.createElement('button');
    button.type = 'button'; button.className = 'round-score';
    if (Number(round.round) === Number(current)) button.classList.add('current');
    const available = round.points != null && round.state !== 'unavailable';
    if (!available) button.classList.add('future');
    button.disabled = !available; button.setAttribute('aria-pressed', 'false');
    button.setAttribute('aria-label', `Round ${round.round}: ${available ? number(round.points) + ' actual points. Show player results' : round.state === 'unavailable' ? 'Results unavailable' : 'Upcoming'}`);
    const label = document.createElement('label'); label.textContent = 'R' + round.round;
    const points = document.createElement('b'); points.textContent = available ? number(round.points) : '-';
    const state = document.createElement('small'); state.textContent = round.state === 'final' ? 'Final' : round.state === 'unavailable' ? 'No data' : !available ? 'Upcoming' : 'So far';
    button.append(label, points, state); button.onclick = () => show(round, button);
    buttons.push(button); grid.append(button);
  });
  reset.onclick = () => {
    section.parentElement.classList.remove('view-history'); panel.hidden = true; reset.hidden = true;
    buttons.forEach(b => {b.classList.remove('selected'); b.setAttribute('aria-pressed', 'false');});
  };
  section.append(heading, grid, note, reset, panel);
  return section;
};
