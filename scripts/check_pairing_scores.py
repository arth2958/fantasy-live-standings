#!/usr/bin/env python3
"""Advisory check of league detail totals against published pairing headers."""
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen

DETAIL = Path('data/league-s50.json')

class PairingHeaders(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_header = False
        self.cell = None
        self.link_id = None
        self.headers = []
        self.cells = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        classes = a.get('class', '').split()
        if tag == 'tr' and 'header-row' in classes:
            self.in_header = True
            self.cells = []
        if not self.in_header:
            return
        if tag == 'th':
            self.cell = {'score': 'cell-score' in classes, 'id': None, 'text': ''}
        if tag == 'a' and self.cell is not None and 'team-link' in classes:
            m = re.fullmatch(r'/team4545/season/\d+/team/(\d+)/', a.get('href', ''))
            if m:
                self.cell['id'] = int(m.group(1))

    def handle_data(self, data):
        if self.in_header and self.cell is not None:
            self.cell['text'] += data

    def handle_endtag(self, tag):
        if tag == 'th' and self.in_header and self.cell is not None:
            self.cells.append(self.cell)
            self.cell = None
        if tag == 'tr' and self.in_header:
            self.headers.append(self.cells)
            self.cells = []
            self.in_header = False

def main():
    d = json.loads(DETAIL.read_text())
    url = f"https://www.lichess4545.com/team4545/season/{d['season']}/round/{d['round']}/pairings/"
    req = Request(url, headers={'User-Agent': 'S50 advisory pairing score check'})
    with urlopen(req, timeout=30) as response:
        page = response.read().decode('utf-8')
    parser = PairingHeaders()
    parser.feed(page)
    official = {}
    for cells in parser.headers:
        if len(cells) < 4 or not cells[0]['id'] or not cells[3]['id'] or not cells[1]['score'] or not cells[2]['score']:
            continue
        for team, score in ((cells[0], cells[1]), (cells[3], cells[2])):
            text = score['text'].strip().replace('½', '.5')
            try:
                points = float(text)
            except ValueError:
                continue
            official[team['id']] = points
    if not official:
        print(f'PAIRING CHECK UNAVAILABLE: no scored team headers parsed from {url}')
        return
    checked = 0
    differences = []
    for name, team in d['teams'].items():
        tid = team.get('team_id')
        if tid not in official:
            continue
        checked += 1
        # Header scores cover this round only. Do not include prior rounds or projections.
        actual = sum(float(p['actual_result']) for p in team['players'] if p['actual_result'] is not None)
        if abs(actual - official[tid]) > 0.001:
            differences.append((tid, name, actual, official[tid]))
    if checked < len(d['teams']):
        print(f'PAIRING CHECK INCOMPLETE: matched {checked}/{len(d["teams"])} team IDs at {url}')
    if differences:
        for tid, name, actual, source in differences:
            print(f'PAIRING SCORE MISMATCH: team {tid} {name!r}: game feed {actual:g}; pairings {source:g}')
    else:
        print(f'Pairing score check: {checked}/{len(d["teams"])} matched teams agree with {url}')

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f'PAIRING CHECK UNAVAILABLE: {type(e).__name__}: {e}', file=sys.stderr)
