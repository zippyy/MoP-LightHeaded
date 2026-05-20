#!/usr/bin/env python3

from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parent.parent
OUTFILE = ROOT / 'tools' / 'midnight_quest_ids.txt'
DB2FILE = ROOT / 'tools' / 'QuestV2.db2'

MIN_QID = 88000
MAX_QID = 99999


def scan_candidate_ids(data: bytes):
    ids = set()

    for offset in range(0, len(data) - 4, 4):
        try:
            value = struct.unpack_from('<I', data, offset)[0]
        except Exception:
            continue

        if MIN_QID <= value <= MAX_QID:
            ids.add(value)

    return sorted(ids)


def load_existing_ids():
    ids = set()

    if not OUTFILE.exists():
        return ids

    for line in OUTFILE.read_text(encoding='utf-8').splitlines():
        line = line.strip()

        if not line or line.startswith('#'):
            continue

        try:
            ids.add(int(line))
        except Exception:
            continue

    return ids


def write_ids(ids):
    output = []
    output.append('# Midnight quest IDs merged from QuestV2.db2 scanning')
    output.append('')

    for qid in sorted(ids):
        output.append(str(qid))

    OUTFILE.write_text('\n'.join(output) + '\n', encoding='utf-8')


def main():
    if not DB2FILE.exists():
        raise SystemExit(f'Missing DB2 file: {DB2FILE}')

    data = DB2FILE.read_bytes()

    existing = load_existing_ids()
    discovered = set(scan_candidate_ids(data))

    merged = existing | discovered

    print(f'[+] Existing IDs: {len(existing)}')
    print(f'[+] DB2 candidate IDs: {len(discovered)}')
    print(f'[+] Total merged IDs: {len(merged)}')

    write_ids(merged)


if __name__ == '__main__':
    main()
