"""WSC GenZ 48 reveal with preview, test and guarded one-time live mode."""
import argparse
import hashlib
import json
import os
import random
import time
import urllib.error
import urllib.request
import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / 'reveal_entries.json'
# Fixed draw seed: same confirmed results always produce the same reveal order.
REVEAL_SEED = 'WSC-GENZ-48-QUALIFIER-DRAW-V1'
LOCK_TITLE = 'WSC48-QUALIFIER-REVEAL-LIVE-STARTED-DO-NOT-RESTART'


def send(content):
    url = os.environ.get('DISCORD_QUALIFIER_WEBHOOK')
    if not url:
        raise RuntimeError('Missing DISCORD_QUALIFIER_WEBHOOK secret')
    payload = json.dumps({
        'username': 'Qualifier Reveal',
        'content': content,
        'allowed_mentions': {'parse': []},
    }).encode('utf-8')
    for attempt in range(5):
        request = urllib.request.Request(
            url, data=payload,
            headers={'Content-Type': 'application/json', 'User-Agent': 'WSCGenZ-Reveal/1.0'},
            method='POST',
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                if response.status not in (200, 204):
                    raise RuntimeError(f'Unexpected Discord status {response.status}')
                return
        except urllib.error.HTTPError as exc:
            if exc.code != 429 or attempt == 4:
                raise RuntimeError(f'Discord HTTP {exc.code}; test stopped') from exc
            try:
                wait = min(120, max(1, float(exc.headers.get('Retry-After', '5'))))
            except ValueError:
                wait = 5
            time.sleep(wait)


def validate_entries(data, require_final=False):
    if data.get('edition') != 48:
        raise ValueError('Expected edition 48')
    canada = data.get('automatic_finalist', {})
    if (canada.get('country') != 'Canada' or canada.get('final_position') != 19
            or not canada.get('youtube_id')):
        raise ValueError('Canada must have a YouTube ID and final position 19')
    entries = data.get('semifinal_entries', [])
    if len(entries) != 43:
        raise ValueError(f'Expected 43 semifinal entries, found {len(entries)}')
    if len({e.get('country') for e in entries}) != 43:
        raise ValueError('Duplicate or missing country names')
    if any(not e.get('youtube_id') for e in entries):
        raise ValueError('Missing YouTube ID')
    for semi, expected in ((1, 21), (2, 22)):
        group = [e for e in entries if e.get('semifinal') == semi]
        if len(group) != expected:
            raise ValueError(f'Semifinal {semi}: expected {expected} entries, found {len(group)}')
        if any(e.get('qualified') not in (True, False, None) for e in group):
            raise ValueError(f'Semifinal {semi}: invalid qualification value')
        confirmed = sum(e['qualified'] is True for e in group)
        pending = sum(e['qualified'] is None for e in group)
        if confirmed > 12:
            raise ValueError(f'Semifinal {semi}: more than 12 qualifiers')
        if require_final and (pending or confirmed != 12):
            raise ValueError(f'Semifinal {semi}: final results not confirmed')
    return entries


def build(data):
    entries = validate_entries(data, require_final=True)
    qualifiers = [e for e in entries if e['qualified'] is True]
    # The order is reproducible, rather than changing on every preview.
    # A change to confirmed results deliberately changes the draw.
    canonical = json.dumps(
        sorted([(e['country'], e['semifinal'], e['youtube_id'], e['qualified'])
                for e in entries]), separators=(',', ':'), ensure_ascii=False
    )
    digest = hashlib.sha256((REVEAL_SEED + canonical).encode('utf-8')).hexdigest()
    rng = random.Random(int(digest, 16))
    finale = {semi: rng.choice([e for e in qualifiers if e['semifinal'] == semi])
              for semi in (1, 2)}
    ordinary = [e for e in qualifiers if e not in finale.values()]
    rng.shuffle(ordinary)

    def announce(entry):
        return f"🎉 **{entry['country'].upper()} QUALIFIES!**\n🎵 https://www.youtube.com/watch?v={entry['youtube_id']}"

    messages = [
        f"🇨🇦 **CANADA IS IN THE GRAND FINAL!**\nAutomatic finalist · Running order **19**\n🎵 https://www.youtube.com/watch?v={data['automatic_finalist']['youtube_id']}",
        '🎤 **WSC GenZ 48 | QUALIFIER REVEAL**\n24 countries will qualify from our two semifinals. Here we go!',
    ]
    messages.extend(announce(entry) for entry in ordinary)
    for semi in (1, 2):
        named = {entry['country'] for entry in ordinary}
        if semi == 2:
            named.add(finale[1]['country'])
        remaining = [entry['country'] for entry in entries
                     if entry['semifinal'] == semi and entry['country'] not in named]
        rng.shuffle(remaining)
        messages.append(
            f"⏳ **SEMIFINAL {semi}: ONE QUALIFYING SPOT LEFT!**\n"
            + 'Still waiting to hear their fate:\n'
            + ' · '.join(remaining)
            + '\n\nThe final qualifier will be revealed in **60 seconds**...'
        )
        messages.append(announce(finale[semi]))
    messages.append('🏆 **ALL 25 GRAND FINALISTS ARE CONFIRMED!**\n24 semifinal qualifiers join 🇨🇦 Canada in the Grand Final. The running order will follow!')
    return messages


def claim_live_once():
    """Create a durable public GitHub issue BEFORE the first Discord message.

    GitHub Actions concurrency serializes live invocations. The issue survives
    runner termination, cancellation, and subsequent workflow invocations.
    If any GitHub API request fails, the reveal fails closed.
    """
    token = os.environ.get('GITHUB_TOKEN') or os.environ.get('GH_TOKEN')
    repo = os.environ.get('GITHUB_REPOSITORY')
    if not token or not repo or '/' not in repo:
        raise RuntimeError('Missing GITHUB_TOKEN or GITHUB_REPOSITORY; live blocked')
    url = f'https://api.github.com/repos/{repo}/issues'
    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28',
        'User-Agent': 'WSCGenZ-Reveal/1.0',
    }
    # Include closed issues so closing the marker cannot accidentally unlock a rerun.
    for page in range(1, 11):
        req = urllib.request.Request(f'{url}?state=all&per_page=100&page={page}', headers=headers)
        with urllib.request.urlopen(req, timeout=30) as response:
            issues = json.load(response)
        if any(issue.get('title') == LOCK_TITLE for issue in issues):
            raise RuntimeError('Live reveal was already started. Refusing to post again.')
        if len(issues) < 100:
            break
    else:
        raise RuntimeError('Too many issues to check safely; live blocked')
    payload = json.dumps({
        'title': LOCK_TITLE,
        'body': 'Single-use safety lock for Edition 48. Created BEFORE the first Discord message. '
                'Do not delete this issue or restart the live workflow. '
                f'Run: {os.environ.get("GITHUB_RUN_ID", "unknown")}.',
    }).encode('utf-8')
    req = urllib.request.Request(url, data=payload, headers={**headers, 'Content-Type': 'application/json'}, method='POST')
    with urllib.request.urlopen(req, timeout=30) as response:
        created = json.load(response)
    if created.get('title') != LOCK_TITLE:
        raise RuntimeError('Live lock creation could not be confirmed; live blocked')
    print(f'Persistent one-time lock created: {created.get("html_url")}', flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['preview', 'test', 'live'], required=True)
    parser.add_argument('--confirm', default='')
    args = parser.parse_args()

    if args.mode == 'test':
        send('🧪 **WSC GenZ 48 | Test**\nThe reveal connection is working. No qualifiers have been revealed.')
        print('Test delivered')
        return

    data = json.loads(DATA.read_text(encoding='utf-8'))
    entries = validate_entries(data)
    if args.mode == 'live':
        if args.confirm != 'REVEAL48':
            raise RuntimeError('Live requires exact confirmation REVEAL48')
        messages = build(data)  # Reject pending or invalid results before creating lock.
        print(f'Validated {len(messages)} reveal messages for live delivery', flush=True)
        claim_live_once()  # Durable safety lock; no Discord messages before this succeeds.
        for i, message in enumerate(messages):
            send(message)
            print(f'Sent message {i+1}/{len(messages)}', flush=True)
            if i < len(messages) - 1:
                time.sleep(60 if message.startswith('⏳') else 30)
        print('Live reveal complete', flush=True)
        return
    print('WSC GenZ 48 | PREVIEW CHECK')
    print('Canada: automatic finalist, Grand Final position 19')
    for semi in (1, 2):
        group = [e for e in entries if e['semifinal'] == semi]
        confirmed = sum(e['qualified'] is True for e in group)
        pending = sum(e['qualified'] is None for e in group)
        print(f'Semifinal {semi}: {len(group)} entries, {confirmed} confirmed qualifiers, {pending} pending results')

    if any(e['qualified'] is None for e in entries):
        print('Full reveal preview unavailable until all votes are confirmed.')
    else:
        for index, message in enumerate(build(data), 1):
            print(f'--- Message {index} ---\n{message}\n')
        print('DRAW IS REPRODUCIBLE: unchanged results produce the same announcement sequence.')
        print('For live use, we will approve and pin the final results and commit before enabling Live.')
    print('PREVIEW ONLY: no Discord messages sent')


if __name__ == '__main__':
    main()
