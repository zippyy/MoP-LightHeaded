#!/usr/bin/env python3

import html
import json
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
OUTFILE = ROOT / 'LightHeaded' / 'Data' / 'LH_Data_Midnight.lua'
QIDFILE = ROOT / 'tools' / 'midnight_quest_ids.txt'

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (compatible; LightHeadedMidnightBot/1.0)'
}

COMMENT_SEP = '\031'
ENTRY_SEP = '\030'


def clean(text: str) -> str:
    text = html.unescape(text or '')
    text = text.replace('\r', '')
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def lua_escape(text: str) -> str:
    return text.replace('\\', '\\\\').replace('"', '\\"')


def load_ids():
    ids = []
    for line in QIDFILE.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        ids.append(int(line))
    return ids


def fetch_wowhead(qid: int):
    url = f'https://www.wowhead.com/quest={qid}'
    print(f'[+] Fetching {url}')

    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, 'html.parser')

    title = None
    h1 = soup.find('h1')
    if h1:
        title = clean(h1.get_text())

    comments = []

    for comment in soup.select('.comment-body')[:25]:
        text = clean(comment.get_text('\n'))
        if len(text) < 20:
            continue
        comments.append({
            'user': 'Wowhead',
            'date': '',
            'body': text,
        })

    return {
        'id': qid,
        'title': title or f'Quest {qid}',
        'comments': comments,
        'url': url,
    }


def build_entry(data):
    qid = data['id']

    header = (
        f'{qid}{COMMENT_SEP}1{COMMENT_SEP}80{COMMENT_SEP}80'
        f'{COMMENT_SEP}NPC{COMMENT_SEP}Unknown{COMMENT_SEP}0'
        f'{COMMENT_SEP}NPC{COMMENT_SEP}Unknown{COMMENT_SEP}0'
        f'{COMMENT_SEP}0{COMMENT_SEP}{COMMENT_SEP}{ENTRY_SEP}'
    )

    lines = []
    lines.append(f'[{qid}] = {{')
    lines.append(f'  "{lua_escape(header)}",')

    if not data['comments']:
        body = f'No parsed comments available yet. Wowhead URL: {data["url"]}'
        comment = (
            f'Wowhead{COMMENT_SEP}0{COMMENT_SEP}5{COMMENT_SEP}0'
            f'{COMMENT_SEP}{COMMENT_SEP}{body}'
        )
        lines.append(f'  "{lua_escape(comment)}",')
    else:
        for c in data['comments']:
            comment = (
                f'{c["user"]}{COMMENT_SEP}0{COMMENT_SEP}5{COMMENT_SEP}0'
                f'{COMMENT_SEP}{c["date"]}{COMMENT_SEP}{c["body"]}'
            )
            lines.append(f'  "{lua_escape(comment)}",')

    lines.append('},')
    return '\n'.join(lines)


def write_pack(entries):
    output = []
    output.append('LH_Data_Midnight = LH_Data_Midnight or {')
    output.append('')

    for entry in entries:
        output.append(build_entry(entry))
        output.append('')

    output.append('}')

    OUTFILE.write_text('\n'.join(output), encoding='utf-8')
    print(f'[+] Wrote {OUTFILE}')


def main():
    entries = []

    for qid in load_ids():
        try:
            entries.append(fetch_wowhead(qid))
            time.sleep(2)
        except Exception as e:
            print(f'[!] Failed {qid}: {e}')

    write_pack(entries)


if __name__ == '__main__':
    main()
