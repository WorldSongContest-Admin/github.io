import argparse
import json
import os
import random
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / 'reveal_entries.json'
STATE = BASE / 'reveal_state.json'


def send(content):
    url = os.environ.get('DISCORD_QUALIFIER_WEBHOOK')
    if not url:
        raise RuntimeError('Missing DISCORD_QUALIFIER_WEBHOOK secret')
    payload = json.dumps({'username': 'Qualifier Reveal', 'content': content, 'allowed_mentions': {'parse': []}}).encode()
    for attempt in range(5):
        request = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json', 'User-Agent': 'WSCGenZ-Reveal/1.0'}, method='POST')
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                if response.status not in (200, 204):
                    raise RuntimeError(f'Unexpected Discord status {response.status}')
                return
        except urllib.error.HTTPError as exc:
            if exc.code != 429 or attempt == 4:
                raise RuntimeError(f'Discord HTTP {exc.code}; stopping to avoid duplicate announcements') from exc
            retry = exc.headers.get('Retry-After', '5')
            try:
                wait = min(120, max(1, float(retry)))
            except ValueError:
                wait = 5
            time.sleep(wait)
    raise RuntimeError('Discord message failed')


def validate(data):
    if data.get('edition') != 48:
        raise ValueError('Expected edition 48')
    canada = data.get('automatic_finalist')
    if not canada or canada.get('country') != 'Canada' or canada.get('final_position') != 19:
        raise ValueError('Canada must be the automatic finalist at position 19')
    if not canada.get('youtube_id'):
        raise ValueError('Canada video missing')
    entries = data.get('semifinal_entries', [])
    for semi in (1, 2):
        group = [e for e in entries if e.get('semifinal') == semi]
        if len(group) != (21 if semi == 1 else 22):
            raise ValueError(f'Semifinal {semi}: expected complete entry list')
        if len([e for e in group if e.get('qualified') is True]) != 12:
            raise ValueError(f'Semifinal {semi}: exactly 12 confirmed qualifiers required')
        if any(e.get('qualified') not in (True, False) for e in group):
            raise ValueError(f'Semifinal {semi}: results not confirmed')
    if len({e['country'] for e in entries}) != len(entries):
        raise ValueError('Duplicate countries')
    if any(not e.get('youtube_id') for e in entries if e['qualified']):
        raise ValueError('A qualifier has no YouTube ID')
    return entries


def build(data):
    entries = validate(data)
    qualifiers = [e for e in entries if e['qualified']]
    rng = random.SystemRandom()
    finale = {semi: rng.choice([e for e in qualifiers if e['semifinal'] == semi]) for semi in (1, 2)}
    ordinary = [e for e in qualifiers if e not in finale.values()]
    rng.shuffle(ordinary)
    def announce(e):
        return f"🎉 **{e['country'].upper()} QUALIFIES!**\n🎵 https://www.youtube.com/watch?v={e['youtube_id']}"
    messages = [f"🇨🇦 **CANADA IS IN THE GRAND FINAL!**\nAutomatic finalist · Running order **19**\n🎵 https://www.youtube.com/watch?v={data['automatic_finalist']['youtube_id']}",
                '🎤 **WSC GenZ 48 | QUALIFIER REVEAL**\n24 countries will qualify from our two semifinals. Here we go!']
    messages.extend(announce(e) for e in ordinary)
    # The final two qualifier reveals are deliberately separated by their own suspense prompts.
    for semi in (1, 2):
        named = {e['country'] for e in ordinary}
        if semi == 2:
            named.add(finale[1]['country'])
        remaining = [e['country'] for e in entries if e['semifinal'] == semi and e['country'] not in named]
        rng.shuffle(remaining)
        messages.append(f"⏳ **SEMIFINAL {semi}: ONE QUALIFYING SPOT LEFT!**\nStill waiting to hear their fate:\n" + ' · '.join(remaining) + '\n\nThe final qualifier will be revealed in **60 seconds**...')
        messages.append(announce(finale[semi]))
    messages.append('🏆 **ALL 25 GRAND FINALISTS ARE CONFIRMED!**\n24 semifinal qualifiers join 🇨🇦 Canada in the Grand Final. The running order will follow!')
    return messages


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['preview', 'test', 'live'], required=True)
    parser.add_argument('--confirm', default='')
    args = parser.parse_args()
    if args.mode == 'test':
        send('🧪 **WSC GenZ 48 | Test**\nThe reveal connection is working. No qualifiers have been revealed.')
        print('Test delivered')
        return
    data = json.loads(DATA.read_text())
       if args.mode == 'preview':
        entries = data.get('semifinal_entries', [])
    for semi, expected in [(1, 21), (2, 22)]:
        group = [e for e in entries if e.get('semifinal') == semi]
        if len(group) != expected:
            raise ValueError(f'Semifinal {semi}: expected {expected} entries')

    print('WSC GenZ 48 | PREVIEW CHECK')
    print('Canada: automatic finalist, Grand Final position 19')

    for semi in (1, 2):
        group = [e for e in entries if e['semifinal'] == semi]
        confirmed = [e for e in group if e.get('qualified') is True]
        pending = [e for e in group if e.get('qualified') is None]
        print(f'Semifinal {semi}: {len(group)} entries, '
              f'{len(confirmed)} confirmed qualifiers, '
              f'{len(pending)} pending results')

    if any(e.get('qualified') is None for e in entries):
        print('Full reveal preview unavailable until all votes are confirmed.')
        print('PREVIEW ONLY: no Discord messages sent')
        return

messages = build(data)
    if args.mode == 'preview':
        for i, message in enumerate(messages, 1):
            print(f'--- Message {i} ---\n{message}\n')
        print('PREVIEW ONLY: no Discord messages sent')
        return
    if args.confirm != 'REVEAL48':
        raise RuntimeError('Live reveal requires exact confirmation REVEAL48')
    # GitHub Actions concurrency + committed state is required to prevent accidental reruns.
    if STATE.exists():
        raise RuntimeError('Reveal state file already exists. Do not rerun live; inspect status first.')
    STATE.write_text(json.dumps({'status': 'started', 'sent': 0}))
    print('Starting live reveal', flush=True)
    for i, message in enumerate(messages):
        # One state write before each request. If a network error happens after Discord
        # accepts a message, do not automatically retry the entire workflow.
        STATE.write_text(json.dumps({'status': 'in_progress', 'next_message': i + 1, 'sent': i}))
        send(message)
        STATE.write_text(json.dumps({'status': 'in_progress', 'next_message': i + 2, 'sent': i + 1}))
        print(f'Sent message {i+1}/{len(messages)}', flush=True)
        if i < len(messages)-1:
            time.sleep(60 if message.startswith('⏳') else 30)
    STATE.write_text(json.dumps({'status': 'complete', 'sent': len(messages)}))

if __name__ == '__main__':
    main()
