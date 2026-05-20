#!/usr/bin/env python3

import csv
import io
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QIDFILE = ROOT / 'tools' / 'midnight_quest_ids.txt'

MIN_QID = 88000
MAX_QID = 99999

WAGO_FILES = {
    'QuestV2': 'https://wago.tools/db2/QuestV2/csv',
    'QuestLineXQuest': 'https://wago.tools/db2/QuestLineXQuest/csv',
    'QuestLine': 'https://wago.tools/db2/QuestLine/csv',
    'ContentTuning': 'https://wago.tools/db2/ContentTuning/csv',
    'AreaTable': 'https://wago.tools/db2/AreaTable/csv',
    'UiMap': 'https://wago.tools/db2/UiMap/csv',
    'QuestInfo': 'https://wago.tools/db2/QuestInfo/csv',
    'QuestSort': 'https://wago.tools/db2/QuestSort/csv',
}

MIDNIGHT_TERMS = [
    'midnight',
    'quelthalas',
    'silvermoon',
    'ghostlands',
    'eversong',
    'sunwell',
    'void',
    'haranir',
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

    with urllib.request.urlopen(req, timeout=180) as resp:
        return resp.read().decode('utf-8', errors='ignore')


def looks_midnight_related(text):
    text = (text or '').lower()
    return any(term in text for term in MIDNIGHT_TERMS)


def parse_csv_rows(text):
    reader = csv.DictReader(io.StringIO(text))
    return list(reader)


def discover_ids_from_rows(rows):
    ids = set()

    for row in rows:
        joined = ' '.join(str(v) for v in row.values())

        related = looks_midnight_related(joined)

        for value in row.values():
            try:
                num = int(str(value))
            except Exception:
                continue

            if MIN_QID <= num <= MAX_QID:
                if related:
                    ids.add(num)

    return ids


def main():
    existing = load_existing_ids()
    discovered = set()

    for name, url in WAGO_FILES.items():
        try:
            print(f'[+] Fetching {name}: {url}')
            text = fetch(url)
            rows = parse_csv_rows(text)
            ids = discover_ids_from_rows(rows)
            discovered |= ids
            print(f'[+] {name}: {len(ids)} candidate Midnight IDs')
        except Exception as e:
            print(f'[!] Failed {name}: {e}')

    merged = sorted(existing | discovered)

    output = []
    output.append('# Midnight quest IDs')
    output.append('# Includes Wago metadata-derived quest IDs')
    output.append('')

    for qid in merged:
        output.append(str(qid))

    QIDFILE.write_text('\n'.join(output) + '\n', encoding='utf-8')

    print(f'[+] Existing IDs: {len(existing)}')
    print(f'[+] Wago metadata IDs: {len(discovered)}')
    print(f'[+] Total merged IDs: {len(merged)}')


if __name__ == '__main__':
    main()
