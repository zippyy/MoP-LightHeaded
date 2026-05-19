#!/usr/bin/env python3

import os
import re
from pathlib import Path
from urllib.parse import quote_plus, urljoin, urlparse

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
QIDFILE = ROOT / 'tools' / 'midnight_quest_ids.txt'
BASE_URL = 'https://www.wowhead.com'
MAX_PAGES = int(os.environ.get('LH_DISCOVER_MAX_PAGES', '250'))
MIN_QID = int(os.environ.get('LH_DISCOVER_MIN_QID', '88000'))
MAX_QID = int(os.environ.get('LH_DISCOVER_MAX_QID', '99999'))

SEARCH_TERMS = [
    'midnight quest',
    'midnight quests',
    'harandar quest',
    'quelthalas quest',
    'silvermoon quest',
    'voidstorm quest',
]

START_URLS = [
    'https://www.wowhead.com/quests/midnight',
    'https://www.wowhead.com/beta/quests/midnight',
    'https://www.wowhead.com/quests',
    'https://www.wowhead.com/beta/quests',
]

for term in SEARCH_TERMS:
    START_URLS.append(f'https://www.wowhead.com/search?q={quote_plus(term)}')
    START_URLS.append(f'https://www.wowhead.com/beta/search?q={quote_plus(term)}')

QUEST_PATTERNS = [
    r'(?:quest=|/quest/)(\d+)',
    r'"id"\s*:\s*(\d+)',
    r'"questId"\s*:\s*(\d+)',
    r'\bid\s*:\s*(\d+)',
    r'\bquestId\s*:\s*(\d+)',
]


def is_candidate_qid(qid: int) -> bool:
    return MIN_QID <= qid <= MAX_QID


def extract_ids(text, ids, source_name='page'):
    if not text:
        return 0

    before = len(ids)

    for pattern in QUEST_PATTERNS:
        for match in re.findall(pattern, text):
            qid = int(match)
            if is_candidate_qid(qid):
                ids.add(qid)

    found = len(ids) - before
    if found:
        print(f'[+] Found {found} new quest IDs from {source_name}')
    return found


def should_crawl(full_url: str) -> bool:
    parsed = urlparse(full_url)

    if parsed.netloc and parsed.netloc not in ('www.wowhead.com', 'wowhead.com'):
        return False

    url = full_url.lower()

    allowed_bits = [
        '/quests',
        '/beta/quests',
        '/search?q=',
        '/beta/search?q=',
        'filter=',
        'page=',
        'midnight',
        'harandar',
        'quel',
        'silvermoon',
    ]

    return any(bit in url for bit in allowed_bits)


def collect_links(page):
    try:
        return page.eval_on_selector_all(
            'a[href]',
            'els => els.map(a => a.getAttribute("href"))'
        ) or []
    except Exception:
        return []


def click_possible_next_pages(page, ids):
    selectors = [
        'a:has-text("Next")',
        'button:has-text("Next")',
        '.listview-band-top a:has-text("Next")',
        '.listview-band-bottom a:has-text("Next")',
    ]

    for _ in range(10):
        clicked = False

        for selector in selectors:
            try:
                locator = page.locator(selector).last
                if locator.count() and locator.is_visible():
                    locator.click(timeout=3000)
                    page.wait_for_timeout(1500)
                    extract_ids(page.content(), ids, 'client-side paged list')
                    clicked = True
                    break
            except Exception:
                continue

        if not clicked:
            break


def collect_page(page, url, ids, discovered_pages):
    print(f'[+] Crawling {url}')

    page.goto(url, wait_until='domcontentloaded', timeout=60000)

    try:
        page.wait_for_selector('body', timeout=15000)
    except PlaywrightTimeoutError:
        print('[!] Body selector timeout; continuing with partial DOM')

    page.wait_for_timeout(4000)

    extract_ids(page.content(), ids, f'HTML {url}')

    try:
        body_text = page.locator('body').inner_text(timeout=10000)
        extract_ids(body_text, ids, f'text {url}')
    except PlaywrightTimeoutError:
        pass

    click_possible_next_pages(page, ids)

    for href in collect_links(page):
        if not href:
            continue

        full = urljoin(BASE_URL, href).split('#')[0]
        extract_ids(full, ids, f'href {url}')

        if should_crawl(full):
            discovered_pages.add(full)


def discover_ids():
    ids = set()
    discovered_pages = set(START_URLS)
    crawled = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125 Safari/537.36',
            locale='en-US',
            timezone_id='America/Denver',
            viewport={'width': 1600, 'height': 1200},
        )

        page = context.new_page()

        while discovered_pages and len(crawled) < MAX_PAGES:
            url = discovered_pages.pop()

            if url in crawled:
                continue

            try:
                collect_page(page, url, ids, discovered_pages)
                crawled.add(url)
            except Exception as e:
                print(f'[!] Failed crawling {url}: {e}')

        page.close()
        context.close()
        browser.close()

    print(f'[+] Crawled {len(crawled)} Wowhead pages')
    print(f'[+] Discovered {len(ids)} candidate Midnight quest IDs')

    return sorted(ids)


def write_seed_file(ids):
    output = []
    output.append('# Midnight quest IDs discovered from Wowhead JS-rendered quest/search/filter pages.')
    output.append('# Generated by tools/discover_midnight_quest_ids.py')
    output.append(f'# Filters: {MIN_QID} <= quest ID <= {MAX_QID}')
    output.append('# One quest ID per line. Blank lines and # comments are ignored.')
    output.append('')

    for qid in ids:
        output.append(str(qid))

    QIDFILE.write_text('\n'.join(output) + '\n', encoding='utf-8')
    print(f'[+] Wrote {len(ids)} quest IDs to {QIDFILE}')


def main():
    ids = discover_ids()

    if not ids:
        raise SystemExit('[!] No Midnight quest IDs were discovered.')

    write_seed_file(ids)


if __name__ == '__main__':
    main()
