"""Simple FAQ scraper.

Usage:
    python scripts/scrape_faq.py <url> [output_file]

This script heuristically attempts to extract question/answer pairs from common FAQ
page structures (headings followed by paragraphs, definition lists, or lists).
It is not guaranteed to work on all sites — you may need to tweak selectors per-site.

IMPORTANT: Only scrape sites you have permission to scrape. Respect robots.txt and TOS.
"""
import sys
import json
import requests
import sys
import json
from pathlib import Path
from scrape_lib import scrape_url

URL = None
OUT = 'data/faqs.json'

if len(sys.argv) < 2:
    print("Usage: python scripts/scrape_faq.py <url> [output_file]")
    sys.exit(1)

URL = sys.argv[1]
if len(sys.argv) > 2:
    OUT = sys.argv[2]

try:
    items = scrape_url(URL)
except Exception as e:
    print(f"Failed to scrape {URL}: {e}")
    sys.exit(1)

out_path = Path(OUT)
out_path.parent.mkdir(parents=True, exist_ok=True)
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(items, f, indent=2, ensure_ascii=False)

print(f"Wrote {len(items)} FAQ items to {OUT}")
        soup = BeautifulSoup(r.text, 'lxml')
