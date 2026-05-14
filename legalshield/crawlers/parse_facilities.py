"""Parse downloaded facility HTML files into structured data.

Reads raw HTML from knowledge/raw/facilities/ and extracts
facility names, addresses, and phones where possible.
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup

from .common import write_parquet

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "knowledge" / "raw" / "facilities"

ADDR_RE = re.compile(r"(〒\d{3}-\d{4}[\s　]*[^\n<]{5,100})")
TEL_RE = re.compile(r"(0\d{1,4}-\d{1,4}-\d{4})")


def parse_html(path: Path, category: str) -> list[dict]:
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            html = f.read()
    except Exception:
        return []

    soup = BeautifulSoup(html, "html.parser")
    records = []

    # Strategy: find tables with addresses
    for table in soup.find_all("table"):
        for tr in table.find_all("tr"):
            text = tr.get_text(" ", strip=True)
            addr = ADDR_RE.search(text)
            tel = TEL_RE.search(text)
            if addr or tel:
                # Extract name from th or first td
                name = ""
                for tag in ("th", "td", "a"):
                    t = tr.find(tag)
                    if t:
                        name = t.get_text(strip=True)
                        if len(name) > 2:
                            break
                records.append({
                    "category": category,
                    "name": name[:80],
                    "address": addr.group(1) if addr else None,
                    "phone": tel.group(1) if tel else None,
                    "source_file": str(path),
                })

    # Strategy 2: find div/li with address patterns
    if not records:
        for tag in soup.find_all(["div", "li", "p"]):
            text = tag.get_text(" ", strip=True)
            addr = ADDR_RE.search(text)
            tel = TEL_RE.search(text)
            if addr or tel:
                name = tag.find(["h3","h4","h5","strong","b","a"])
                name_text = name.get_text(strip=True)[:60] if name else ""
                records.append({
                    "category": category,
                    "name": name_text,
                    "address": addr.group(1) if addr else None,
                    "phone": tel.group(1) if tel else None,
                    "source_file": str(path),
                })

    return records


def main() -> None:
    all_records = []
    for subdir in RAW.iterdir():
        if subdir.is_dir():
            category = subdir.name
            files = list(subdir.glob("*.html"))
            print(f"Parsing {category}: {len(files)} files")
            for f in files:
                records = parse_html(f, category)
                all_records.extend(records)

    if all_records:
        df = pd.DataFrame(all_records)
        out = ROOT / "knowledge" / "parsed_facilities.parquet"
        df.to_parquet(out)
        print(f"\n[ok] {out}")
        print(f"     rows={len(df)}")
        print(f"     categories={df['category'].unique().tolist()}")
    else:
        print("[warn] no facility records parsed")


if __name__ == "__main__":
    main()
