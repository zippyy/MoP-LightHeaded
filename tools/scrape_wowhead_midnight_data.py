#!/usr/bin/env python3

import html
import os
import re
from pathlib import Path

from bs4 import BeautifulSoup
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
QIDFILE = ROOT / 'tools' / 'midnight_quest_ids.txt'
OUTFILE = ROOT / 'LightHeaded' / 'Data' / 'LH_Data_Midnight.lua'

COMMENT_SEP = '\031'
ENTRY_SEP = '\030'
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125 Safari/537.36'

MAX_QUESTS = int(os.environ.get('LH_MAX_QUESTS', '750'))
START_INDEX = int(os.environ.get('LH_START_INDEX', '0'))


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

        if line.isdigit():
            ids.append(int(line))

    ids = sorted(set(ids))

    end_index = START_INDEX + MAX_QUESTS
    sliced = ids[START_INDEX:end_index]

    print(f'[+] Total quest IDs available: {len(ids)}')
    print(f'[+] Processing range: {START_INDEX} -> {end_index}')
    print(f'[+] Selected quest IDs: {len(sliced)}')

    return sliced


def dump_globals(page):
    try:
        result = page.evaluate("""
            () => {
                const keys = ['g_quests', 'g_mapperData', 'g_listviews', 'g_pageInfo'];
                const chunks = [];

                for (const key of keys) {
                    try {
                        if (window[key]) {
                            chunks.push(JSON.stringify(window[key]).slice(0, 400000));
                        }
                    } catch (e) {}
                }

                return chunks.join('\\n');
            }
        """)

        return result or ''
    except Exception:
        return ''


def extract_comments_from_globals(blob):
    comments = []

    try:
        for match in re.findall(r'"body":"(.*?)"', blob):
            body = clean(match)

            if len(body) < 25:
                continue

            comments.append({
                'user': 'Wowhead',
                'date': '',
                'body': body,
            })
    except Exception:
        pass

    return comments[:15]


def scrape_quest(page, qid):
    url = f'https://www.wowhead.com/quest={qid}'
    print(f'[+] Scraping {url}')

    try:
        page.goto(url, wait_until='domcontentloaded', timeout=15000)
        page.wait_for_timeout(750)

        html_text = page.content()
        globals_blob = dump_globals(page)

        soup = BeautifulSoup(html_text, 'html.parser')

        title = None

        h1 = soup.find('h1')
        if h1:
            title = clean(h1.get_text())

        if not title:
            match = re.search(r'"name":"([^"]+)"', globals_blob)
            if match:
                title = clean(match.group(1))

        if not title:
            return None

        comments = []

        for node in soup.select('.comment-body')[:15]:
            body = clean(node.get_text('\n'))

            if len(body) < 25:
                continue

            comments.append({
                'user': 'Wowhead',
                'date': '',
                'body': body,
            })

        if not comments:
            comments = extract_comments_from_globals(globals_blob)

        return {
            'id': qid,
            'title': title,
            'comments': comments,
        }

    except PlaywrightTimeoutError:
        return None
    except Exception as e:
        print(f'[!] Failed {qid}: {e}')
        return None


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
        placeholder = (
            f'Wowhead{COMMENT_SEP}0{COMMENT_SEP}5{COMMENT_SEP}0'
            f'{COMMENT_SEP}{COMMENT_SEP}No comments scraped yet.'
        )
        lines.append(f'  "{lua_escape(placeholder)}",')
    else:
        for comment in data['comments']:
            row = (
                f'{comment["user"]}{COMMENT_SEP}0{COMMENT_SEP}5{COMMENT_SEP}0'
                f'{COMMENT_SEP}{comment["date"]}{COMMENT_SEP}{comment["body"]}'
            )
            lines.append(f'  "{lua_escape(row)}",')

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


def main():
    ids = load_ids()
    entries = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        context = browser.new_context(
            user_agent=USER_AGENT,
            locale='en-US',
            viewport={'width': 1280, 'height': 720},
        )

        page = context.new_page()

        page.route(
            '**/*',
            lambda route: route.abort()
            if route.request.resource_type in ['image', 'media', 'font']
            else route.continue_()
        )

        for index, qid in enumerate(ids, start=1):
            result = scrape_quest(page, qid)

            if result:
                entries.append(result)

            if index % 50 == 0:
                print(f'[+] Progress: {index}/{len(ids)}')
                write_pack(entries)

        page.close()
        context.close()
        browser.close()

    print(f'[+] Scraped {len(entries)} valid quests')

    write_pack(entries)

    print(f'[+] Wrote {OUTFILE}')


if __name__ == '__main__':
    main()
