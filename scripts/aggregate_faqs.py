"""Aggregate FAQs from a list of URLs using the scraper.

Usage:
    python scripts/aggregate_faqs.py [urls_file]

Default urls file: scripts/faq_urls.txt
"""
import sys
import os
import json
import time
from scrape_lib import scrape_url
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / 'scripts'
DATA = ROOT / 'data'
URLS_FILE = Path(sys.argv[1]) if len(sys.argv) > 1 else SCRIPTS / 'faq_urls.txt'
OUT_FILE = DATA / 'faqs.json'
TEMP_DIR = DATA / 'faqs_raw'
RATE_DELAY = 2.0  # seconds between requests

TEMP_DIR.mkdir(parents=True, exist_ok=True)

if not URLS_FILE.exists():
    print(f"URLs file not found: {URLS_FILE}")
    sys.exit(1)

with open(URLS_FILE, 'r', encoding='utf-8') as f:
    urls = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]

print(f"Found {len(urls)} URLs to process")

all_items = []
results = []

for i, url in enumerate(urls, start=1):
    safe_name = url.replace('://', '_').replace('/', '_')[:100]
    out_path = TEMP_DIR / f"site_{i}_{safe_name}.json"
    print(f"[{i}/{len(urls)}] Scraping {url} -> {out_path}")
    try:
        items = scrape_url(url)
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(items, f, indent=2, ensure_ascii=False)
        print(f"  -> {len(items)} items")
        results.append({'url': url, 'count': len(items), 'file': str(out_path)})
        for it in items:
            it['source'] = url
            all_items.append(it)
    except Exception as e:
        print(f"  Failed to scrape {url}: {e}")
    # polite delay
    time.sleep(RATE_DELAY)

print(f"Collected {len(all_items)} raw items from {len(urls)} sites")

# Deduplicate: normalize question
import re

def normalize_q(q):
    q = q or ''
    q = q.strip().lower()
    q = re.sub(r"\s+", ' ', q)
    q = q.strip(" '")
    return q

seen = set()
unique = []
for it in all_items:
    q = normalize_q(it.get('question'))
    if not q or not it.get('answer'):
        continue
    if q in seen:
        continue
    seen.add(q)
    unique.append({'question': it.get('question').strip(), 'answer': it.get('answer').strip(), 'source': it.get('source')})

print(f"After dedupe: {len(unique)} unique FAQs")

# Cap to 1000
MAX = 1000
if len(unique) > MAX:
    unique = unique[:MAX]
    print(f"Capped to first {MAX} items")

# Backup existing file
if OUT_FILE.exists():
    bak = OUT_FILE.with_suffix('.json.bak')
    OUT_FILE.replace(bak)
    print(f"Backed up existing {OUT_FILE} to {bak}")

with open(OUT_FILE, 'w', encoding='utf-8') as f:
    json.dump(unique, f, indent=2, ensure_ascii=False)

print(f"Wrote {len(unique)} FAQs to {OUT_FILE}")
print("Summary:")
for r in results:
    print(f" - {r['url']}: {r['count']} items -> {r['file']}")
