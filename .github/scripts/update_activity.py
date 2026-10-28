"""Render actual daily GitHub contribution counts as an SVG chart."""
import argparse
from datetime import date, datetime, timedelta, timezone
from html import escape
import json
import math
import os
from pathlib import Path
import urllib.request

QUERY = '''query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}'''


def fetch_calendar(login):
    now = datetime.now(timezone.utc)
    start = datetime.combine(now.date() - timedelta(days=30), datetime.min.time(), tzinfo=timezone.utc)
    token = os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
    if not token:
        raise RuntimeError('Set GH_TOKEN or GITHUB_TOKEN to read the contribution calendar.')
    payload = {'query': QUERY, 'variables': {
        'login': login,
        'from': start.isoformat().replace('+00:00', 'Z'),
        'to': now.isoformat().replace('+00:00', 'Z'),
    }}
    request = urllib.request.Request('https://api.github.com/graphql', data=json.dumps(payload).encode('utf-8'),
        headers={'Authorization': 'Bearer ' + token, 'User-Agent': 'GitHub-Profile-Activity', 'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=30) as response:
        result = json.load(response)
    if result.get('errors'):
        raise RuntimeError('GitHub could not return the contribution calendar.')
    return result


def render(result, login):
    calendar = result['data']['user']['contributionsCollection']['contributionCalendar']
    days = sorted((day for week in calendar['weeks'] for day in week['contributionDays']), key=lambda day: day['date'])[-31:]
    if not days:
        raise RuntimeError('The calendar was empty; keeping the previous chart.')
    left, right, top, bottom = 64, 1012, 88, 252
    ymax = max(4, math.ceil(max(day['contributionCount'] for day in days) * 1.15 / 4) * 4)
    points = [(left + i*(right-left)/max(1,len(days)-1), bottom-day['contributionCount']*(bottom-top)/ymax) for i,day in enumerate(days)]
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="1040" height="330" viewBox="0 0 1040 330" role="img" aria-labelledby="title desc">',
        '<title id="title">Contribution Activity</title>',
        f'<desc id="desc">Daily GitHub contributions for {escape(login)}, from {days[0]["date"]} to {days[-1]["date"]}.</desc>',
        '<defs><linearGradient id="area" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#38bdf8" stop-opacity=".3"/><stop offset="1" stop-color="#6366f1" stop-opacity=".015"/></linearGradient></defs>',
        '<rect width="1040" height="330" rx="14" fill="#0d1117"/>',
        '<g font-family="Arial, Helvetica, sans-serif">',
        '<text x="32" y="36" fill="#c7d2fe" font-size="21" font-weight="700">Contribution Activity</text>',
        '<text x="32" y="60" fill="#94a3b8" font-size="12">Daily contributions over the last 31 days</text>']
    for tick in range(5):
        value = ymax*tick/4
        y = bottom-(bottom-top)*tick/4
        svg.append(f'<path d="M{left} {y:.1f}H{right}" stroke="#243040" stroke-width="1" stroke-dasharray="3 6"/>')
        svg.append(f'<text x="{left-14}" y="{y+4:.1f}" text-anchor="end" fill="#94a3b8" font-size="11">{value:g}</text>')
    coords = ' '.join(f'{x:.1f},{y:.1f}' for x,y in points)
    svg.append(f'<polygon points="{left},{bottom} {coords} {right},{bottom}" fill="url(#area)"/>')
    svg.append(f'<polyline points="{coords}" fill="none" stroke="#38bdf8" stroke-width="2.4" stroke-linejoin="round" stroke-linecap="round"/>')
    for day,(x,y) in zip(days,points):
        svg.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.3" fill="#a78bfa" stroke="#0d1117" stroke-width="1.5"><title>{day["date"]}: {day["contributionCount"]} contributions</title></circle>')
    for i in sorted(set([0,len(days)-1]+list(range(5,len(days)-1,5)))):
        label = date.fromisoformat(days[i]['date']).strftime('%b %d')
        svg.append(f'<text x="{points[i][0]:.1f}" y="278" text-anchor="middle" fill="#94a3b8" font-size="11">{label}</text>')
    svg.append(f'<text x="32" y="311" fill="#64748b" font-size="11">Source: GitHub contribution calendar | Updated {days[-1]["date"]} UTC</text>')
    svg.append('</g></svg>\n')
    return '\n'.join(svg)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path)
    parser.add_argument('--user', default='HassanABahaa')
    args = parser.parse_args()
    result = json.loads(args.input.read_text(encoding='utf-8-sig')) if args.input else fetch_calendar(args.user)
    content = render(result,args.user)
    output = Path(__file__).resolve().parents[2]/'assets'/'contribution-activity.svg'
    output.parent.mkdir(parents=True,exist_ok=True)
    if not output.exists() or output.read_text(encoding='utf-8')!=content:
        temporary = output.with_suffix('.tmp')
        temporary.write_text(content,encoding='utf-8')
        temporary.replace(output)
    print('Contribution activity chart is up to date.')


if __name__=='__main__':
    main()
