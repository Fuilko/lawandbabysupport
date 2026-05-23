"""Quick exploration of CALL4 site structure to find case/lawsuit detail pages."""
import requests
from bs4 import BeautifulSoup
import re

UA = {"User-Agent": "Mozilla/5.0 LegalShield-Research/1.0 (academic research)"}

print("=" * 60)
print("1. Story page detail - looking for project/case sublinks")
print("=" * 60)
r = requests.get("https://www.call4.jp/story/?p=2457", timeout=15, headers=UA)
soup = BeautifulSoup(r.text, "lxml")

urls = set()
for a in soup.find_all("a", href=True):
    h = a["href"]
    if "call4.jp" in h or h.startswith("/"):
        urls.add(h)
paths = set()
for u in urls:
    if u.startswith("http"):
        u = u.split("call4.jp")[-1]
    paths.add(u.split("#")[0])
for p in sorted(paths):
    print(" ", p)

print()
print("=" * 60)
print("2. Probing common case-list paths")
print("=" * 60)
for path in ["/info/", "/info/list", "/project/", "/projects/", "/case/", "/cases/", "/litigation/",
             "/all/", "/lawsuit/", "/courtcase/", "/categories/", "/category/", "/topic/"]:
    try:
        r = requests.get(f"https://www.call4.jp{path}", timeout=10, headers=UA)
        title = ""
        if r.status_code == 200:
            s = BeautifulSoup(r.text, "lxml")
            t = s.find("title")
            title = t.get_text(strip=True)[:60] if t else ""
        print(f"  {path:30s} HTTP {r.status_code} len={len(r.text):6d}  {title}")
    except Exception as e:
        print(f"  {path}: ERR {e}")

print()
print("=" * 60)
print("3. Inspect homepage for case/project navigation")
print("=" * 60)
r = requests.get("https://www.call4.jp/", timeout=15, headers=UA)
soup = BeautifulSoup(r.text, "lxml")
# Navigation menus
for nav in soup.find_all(["nav", "header"])[:3]:
    print("--- nav/header ---")
    for a in nav.find_all("a", href=True)[:30]:
        print(f"  [{a.get_text(strip=True)[:30]}] -> {a['href']}")

print()
print("=" * 60)
print("4. Scan homepage text for case URL patterns")
print("=" * 60)
patterns = re.findall(r'/(?:info|project|case|lawsuit|courtcase|cat)/[^\s"\'<>]*', r.text)
unique = sorted(set(patterns))
for u in unique[:40]:
    print(" ", u)
