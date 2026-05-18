#!/usr/bin/env python3

import html
import re
import time
from pathlib import Path

from bs4 import BeautifulSoup
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUTFILE = ROOT / 'LightHeaded' / 'Data' / 'LH_Data_Midnight.lua'
QIDFILE = ROOT / 'tools' / 'midnight_quest_ids.txt'

COMMENT_SEP = '\031'
ENTRY_SEP = '\030'
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125 Safari/537.36'


def clean(text: str) -> str:
    text = html.unescape(text or '')
    text = text.replace('\r', '')
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def lua_escape(text: str) -> str:
    return text.replace('\\', '\\\\').replace('"', '\\"')


def load_ids():
    ids = set()

    for line in QIDFILE.read_text(encoding='utf-8').splitlines():
        line = line.strip()

        if not line or line.startswith('#'):
            continue

        if '-' in line:
            start, end = line.split('-', 1)
            start = int(start.strip())
            end = int(end.strip())
            for qid in range(start, end + 1):
                ids.add(qid)
        else:
            ids.add(int(line))

    return sorted(ids)


def parse_quest_html(qid: int, url: str, raw_html: str):
    if not raw_html:
        return None

    lowered = raw_html.lower()
    blocked_markers = [
        '403 forbidden',
        'access denied',
        'attention required',
        'cloudflare',
    ]

    if any(marker in lowered for marker in blocked_markers):
        print(f'[-] Blocked or challenged for {qid}')
        return None

    soup = BeautifulSoup(raw_html, 'html.parser')

    h1 = soup.find('h1')
    title = clean(h1.get_text()) if h1 else None

    invalid_markers = [
        'database error',
        'not found',
        "this quest doesn't exist",
        'page not found',
    ]

    body_text = clean(soup.get_text(' ')[:8000]).lower()

    if not title:
        print(f'[-] No title for {qid}')
        return None

    if any(marker in body_text for marker in invalid_markers):
        print(f'[-] Invalid quest page for {qid}')
        return None

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
        'title': title,
        'comments': comments,
        'url': url,
    }


def fetch_wowhead_page(context, qid: int):
    url = f'https://www.wowhead.com/quest={qid}'
    print(f'[+] Fetching {url}')

    page = context.new_page()

    try:
        page.goto(url, wait_until='domcontentloaded', timeout=60000)
        try:
            page.wait_for_selector('h1', timeout=15000)
        except PlaywrightTimeoutError:
            print(f'[!] No h1 rendered quickly for {qid}; using current page content')

        page.wait_for_timeout(1500)
        raw_html = page.content()
        return parse_quest_html(qid, url, raw_html)

    except PlaywrightTimeoutError:
        print(f'[-] Timeout for {qid}')
        return None
    except Exception as e:
        print(f'[!] Browser fetch failed for {qid}: {e}')
        return None
    finally:
        page.close()


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

    ids = load_ids()
    print(f'[+] Loaded {len(ids)} quest IDs')

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=USER_AGENT,
            locale='en-US',
            timezone_id='America/Denver',
            viewport={'width': 1600, 'height': 1200},
        )

        for qid in ids:
            result = fetch_wowhead_page(context, qid)
            if result:
                entries.append(result)
            time.sleep(1)

        context.close()
        browser.close()

    print(f'[+] Valid quests collected: {len(entries)}')
    write_pack(entries)


if __name__ == '__main__':
    main()
