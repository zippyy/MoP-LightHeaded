#!/usr/bin/env python3

import json
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QIDFILE = ROOT / 'tools' / 'midnight_quest_ids.txt'

MIN_QID = 88000
MAX_QID = 99999

WAGO_URLS = [
    'https://wago.tools/db2/QuestV2/csv',
    'https://wago.tools/db2/QuestV2/json',
]


def load_existing_ids():
    ids = set()

    if not QIDFILE.exists():
        return ids

    for line in QIDFILE.read_text(encoding='utf-8').splitlines():
        line = line.strip()

        if not line or line.startswith('#'):
            continue

        if line.isdigit():
            ids.add(int(line))

    return ids


def fetch(url):
    req = urllib.request.Request(
        url,
        headers={
            'User-Agent': 'Mozilla/5.0',
        },
    )

    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read().decode('utf-8', errors='ignore')


def extract_ids_from_text(text):
    ids = set()

    for match in re.findall(r'\b(9\d{4})\b', text):
        qid = int(match)

        if MIN_QID <= qid <= MAX_QID:
            ids.add(qid)

    return ids


def main():
    existing = load_existing_ids()
    discovered = set()

    for url in WAGO_URLS:
        try:
            print(f'[+] Fetching {url}')
            text = fetch(url)
            ids = extract_ids_from_text(text)
            print(f'[+] Found {len(ids)} IDs from {url}')
            discovered |= ids
        except Exception as e:
            print(f'[!] Failed fetching {url}: {e}')

    merged = sorted(existing | discovered)

    output = []
    output.append('# Midnight quest IDs')
    output.append('# Includes Wago.tools-derived quest IDs')
    output.append('')

    for qid in merged:
        output.append(str(qid))

    QIDFILE.write_text('\n'.join(output) + '\n', encoding='utf-8')

    print(f'[+] Existing IDs: {len(existing)}')
    print(f'[+] Wago.tools IDs: {len(discovered)}')
    print(f'[+] Total merged IDs: {len(merged)}')


if __name__ == '__main__':
    main()
