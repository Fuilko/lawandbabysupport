"""Examine a single CALL4 case page to understand its structure."""
import requests
from bs4 import BeautifulSoup

UA = {"User-Agent": "Mozilla/5.0 LegalShield-Research/1.0"}
url = "https://www.call4.jp/info.php?type=items&id=I0000031"
r = requests.get(url, timeout=15, headers=UA)
soup = BeautifulSoup(r.text, "lxml")

print("=" * 70)
print("Case page structure analysis: I0000031")
print("=" * 70)

# All sections / divs with distinctive classes
print("\n--- Section/div classes (top-level) ---")
main = soup.find("main") or soup.body
if main:
    for el in main.find_all(["section", "div"], class_=True, recursive=False)[:30]:
        cls = " ".join(el.get("class", []))
        print(f"  div.{cls[:50]}")

# Look for meta tags
print("\n--- OG/Twitter meta ---")
for m in soup.find_all("meta"):
    if m.get("property") or m.get("name", "").startswith(("og:", "twitter:")):
        prop = m.get("property") or m.get("name")
        cont = (m.get("content") or "")[:120]
        if prop in ("og:title", "og:description", "og:image", "description", "keywords"):
            print(f"  {prop}: {cont}")

# Find any tables (often used for case metadata)
print("\n--- Tables ---")
for t in soup.find_all("table")[:5]:
    rows = t.find_all("tr")
    print(f"  Table with {len(rows)} rows:")
    for r in rows[:10]:
        cells = [c.get_text(strip=True)[:60] for c in r.find_all(["th", "td"])]
        print(f"    {cells}")

# Find dl (definition list) - often used for structured info
print("\n--- Definition lists ---")
for dl in soup.find_all("dl")[:5]:
    items = list(zip(dl.find_all("dt"), dl.find_all("dd")))
    for dt, dd in items[:10]:
        print(f"  {dt.get_text(strip=True)[:40]} = {dd.get_text(strip=True)[:80]}")

# Main text content blocks
print("\n--- Long paragraphs ---")
for p in soup.find_all("p"):
    txt = p.get_text(strip=True)
    if len(txt) > 100:
        print(f"  • {txt[:150]}...")

# All non-policy PDFs and any document downloads
print("\n--- All file links (PDFs and docs) ---")
for a in soup.find_all("a", href=True):
    h = a["href"]
    if any(h.lower().endswith(ext) for ext in [".pdf", ".docx", ".doc"]):
        if "Privacy" not in h and "Cookie" not in h:
            print(f"  {h}  [{a.get_text(strip=True)[:40]}]")

# Save raw HTML for inspection
with open("d:/projects/LegalShield/scripts/sample_call4_case.html", "w", encoding="utf-8") as f:
    f.write(r.text)
print("\nSaved raw HTML to scripts/sample_call4_case.html")
