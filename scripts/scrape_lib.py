"""Reusable scraping helpers for FAQ pages."""
import requests
from bs4 import BeautifulSoup
import json
import re

DEFAULT_HEADERS = {
    'User-Agent': 'faq-scraper/1.0 (+https://example.com)'
}

def fetch_html(url, timeout=10):
    resp = requests.get(url, timeout=timeout, headers=DEFAULT_HEADERS)
    resp.raise_for_status()
    text = resp.text
    try:
        soup = BeautifulSoup(text, 'lxml')
    except Exception:
        soup = BeautifulSoup(text, 'html.parser')
    return soup


def extract_faqs_from_soup(soup):
    faqs = []
    # Strategy 1: dl/dt/dd
    for dl in soup.find_all('dl'):
        dts = dl.find_all('dt')
        dds = dl.find_all('dd')
        for dt, dd in zip(dts, dds):
            q = dt.get_text(separator=' ', strip=True)
            a = dd.get_text(separator=' ', strip=True)
            if q and a:
                faqs.append({'question': q, 'answer': a})

    # Strategy 2: headings followed by paragraph(s)
    for h in soup.find_all(['h2', 'h3', 'h4']):
        q = h.get_text(separator=' ', strip=True)
        a_parts = []
        for sib in h.next_siblings:
            if getattr(sib, 'name', None) and sib.name.startswith('h'):
                break
            if getattr(sib, 'get_text', None):
                text = sib.get_text(separator=' ', strip=True)
                if text:
                    a_parts.append(text)
        if q and a_parts:
            a = '\n'.join(a_parts).strip()
            faqs.append({'question': q, 'answer': a})

    # Strategy 3: .faq/.question classes
    for qel in soup.select('.faq, .question, .faq-question'):
        q = qel.get_text(separator=' ', strip=True)
        ans = qel.find_next_sibling(class_='answer') or qel.find_next(class_='answer')
        if ans:
            a = ans.get_text(separator=' ', strip=True)
            faqs.append({'question': q, 'answer': a})

    # Strategy 4: li pattern
    for li in soup.find_all('li'):
        text = li.get_text(separator=' ', strip=True)
        if '?' in text and len(text.split('?')) > 1:
            parts = text.split('?')
            q = parts[0].strip() + '?'
            a = '?'.join(parts[1:]).strip()
            if q and a:
                faqs.append({'question': q, 'answer': a})

    # dedupe preserving order
    seen = set()
    uniq = []
    for item in faqs:
        q = item.get('question','').strip()
        if not q:
            continue
        key = re.sub(r"\s+"," ", q.lower())
        if key in seen:
            continue
        seen.add(key)
        uniq.append(item)
    return uniq


def scrape_url(url, timeout=10):
    try:
        soup = fetch_html(url, timeout=timeout)
        items = extract_faqs_from_soup(soup)
        return items
    except Exception as e:
        raise
