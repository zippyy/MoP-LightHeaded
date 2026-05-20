#!/usr/bin/env python3

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QIDFILE = ROOT / 'tools' / 'midnight_quest_ids.txt'
OUTFILE = ROOT / 'LightHeaded' / 'Data' / 'LH_Data_Midnight_Static.lua'

COMMENT_SEP = '\031'
ENTRY_SEP = '\030'


def load_ids():
    ids = []

    for line in QIDFILE.read_text(encoding='utf-8').splitlines():
        line = line.strip()

        if not line or line.startswith('#'):
            continue

        if line.isdigit():
            ids.append(int(line))

    return sorted(set(ids))


def build_entry(qid):
    header = (
        f'{qid}{COMMENT_SEP}1{COMMENT_SEP}80{COMMENT_SEP}80'
        f'{COMMENT_SEP}NPC{COMMENT_SEP}Unknown{COMMENT_SEP}0'
        f'{COMMENT_SEP}NPC{COMMENT_SEP}Unknown{COMMENT_SEP}0'
        f'{COMMENT_SEP}0{COMMENT_SEP}{COMMENT_SEP}{ENTRY_SEP}'
    )

    comment = (
        f'Midnight{COMMENT_SEP}0{COMMENT_SEP}5{COMMENT_SEP}0'
        f'{COMMENT_SEP}{COMMENT_SEP}Auto-generated Midnight quest placeholder.'
    )

    lines = []
    lines.append(f'[{qid}] = {{')
    lines.append(f'  "{header}",')
    lines.append(f'  "{comment}",')
    lines.append('},')

    return '\n'.join(lines)


def main():
    ids = load_ids()

    output = []
    output.append('LH_Data_Midnight = LH_Data_Midnight or {')
    output.append('')

    for qid in ids:
        output.append(build_entry(qid))
        output.append('')

    output.append('}')

    OUTFILE.write_text('\n'.join(output), encoding='utf-8')

    print(f'[+] Loaded {len(ids)} quest IDs')
    print(f'[+] Wrote static Midnight data pack: {OUTFILE}')


if __name__ == '__main__':
    main()
