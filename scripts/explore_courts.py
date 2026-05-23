"""Explore 裁判所 forms page structure."""
import sys
import io
import requests
from bs4 import BeautifulSoup

# Force UTF-8 output for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

UA = {"User-Agent": "Mozilla/5.0 LegalShield-Research/1.0"}
BASE = "https://www.courts.go.jp"

# Main 申立て書式 hub
r = requests.get(f"{BASE}/saiban/syosiki/index.html", timeout=15, headers=UA)
r.encoding = r.apparent_encoding or "utf-8"
print(f"HTTP {r.status_code} len={len(r.text)} encoding={r.encoding}")
soup = BeautifulSoup(r.text, "lxml")
t = soup.find("title")
print("Title:", t.get_text(strip=True) if t else "")
print()

print("=== All form-related links ===")
form_links = []
for a in soup.find_all("a", href=True):
    h = a["href"]
    txt = a.get_text(strip=True)
    if "syosiki" in h:
        # Absolute URL
        if h.startswith("/"):
            h_full = BASE + h
        elif h.startswith("http"):
            h_full = h
        else:
            h_full = BASE + "/saiban/syosiki/" + h
        form_links.append((h_full, txt))
        print(f"  {h_full}\n     [{txt[:60]}]")

print(f"\nTotal form-category links: {len(form_links)}")
