import csv
import re
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

START_URL = "https://www.eggsa.org/sarecords/index.php/muster-rolls/muster-rolls-den-haag-copies/300-free-men-vrijluijden-1673-tabular-format"
OUT_CSV = "eggsa_vrijluijden_1673_raw.csv"

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; vox-capensis; +noncommercial)"}

def extract_article_text_and_next(html: str, base_url: str):
    soup = BeautifulSoup(html, "html.parser")

    # Main article container on Joomla pages like this is typically "item-page"
    item = soup.select_one(".item-page") or soup.body
    text = item.get_text("\n", strip=True)

    # Find "Next" link (pagination between articles)
    next_a = soup.find("a", string=re.compile(r"^\s*Next\s*$", re.I))
    next_url = urljoin(base_url, next_a["href"]) if next_a and next_a.get("href") else None
    return text, next_url

def extract_rows_from_text(text: str):
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

    # Start at the line after the header-ish line containing "tabular format"
    start_idx = None
    for i, ln in enumerate(lines):
        if "tabular format" in ln.lower():
            start_idx = i + 1
            break
    if start_idx is None:
        return []

    rows = []
    for ln in lines[start_idx:]:
        # Stop at Source:
        if ln.lower().startswith("source:"):
            break
        # Skip obvious non-data lines
        if ln.lower().startswith("written by") or ln.lower().startswith("hits:"):
            continue
        if ln in ("Prev", "Next"):
            continue

        # Heuristic: keep lines that look like entries (most start with a name or "-")
        if ln[0].isalpha() or ln.startswith("-"):
            rows.append(ln)

    return rows

def main():
    url = START_URL
    seen = set()
    all_rows = []

    while url and url not in seen:
        seen.add(url)
        r = requests.get(url, headers=HEADERS, timeout=30)
        r.raise_for_status()

        text, next_url = extract_article_text_and_next(r.text, url)
        all_rows.extend(extract_rows_from_text(text))

        # be polite to the site
        time.sleep(1.0)
        url = next_url  # NOTE: for THIS dataset, Next jumps to the PDF page, not another “table page”

    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["raw_row"])
        for row in all_rows:
            w.writerow([row])

    print(f"Wrote {len(all_rows)} rows to {OUT_CSV}")

if __name__ == "__main__":
    main()
