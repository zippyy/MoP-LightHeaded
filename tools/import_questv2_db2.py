#!/usr/bin/env python3

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QIDFILE = ROOT / 'tools' / 'midnight_quest_ids.txt'
DB2FILE = ROOT / 'tools' / 'QuestV2.db2'

MIN_QID = 88000
MAX_QID = 99999


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


def extract_candidate_ids(blob: bytes):
    ids = set()

    # DB2 files contain many integer references.
    # We scan for plausible quest ID clusters directly from the binary.
    for match in re.findall(rb'(9\d{4})', blob):
        try:
            qid = int(match.decode())
        except Exception:
            continue

        if MIN_QID <= qid <= MAX_QID:
            ids.add(qid)

    return ids


def main():
    if not DB2FILE.exists():
        raise SystemExit(f'Missing DB2 file: {DB2FILE}')

    existing = load_existing_ids()

    blob = DB2FILE.read_bytes()
    discovered = extract_candidate_ids(blob)

    merged = sorted(existing | discovered)

    output = []
    output.append('# Midnight quest IDs')
    output.append('# Includes DB2-derived candidate quest IDs')
    output.append('')

    for qid in merged:
        output.append(str(qid))

    QIDFILE.write_text('\n'.join(output) + '\n', encoding='utf-8')

    print(f'[+] Existing IDs: {len(existing)}')
    print(f'[+] DB2 candidate IDs: {len(discovered)}')
    print(f'[+] Total merged IDs: {len(merged)}')


if __name__ == '__main__':
    main()
