"""Probe e-Gov 法令 API health (v1, v2, plain) and discover correct endpoint."""
import json, urllib.parse, requests, sys
from pathlib import Path

LIST = Path(r"D:\projects\LegalShield\data_set\law\list.json")
data = json.loads(LIST.read_text(encoding="utf-8"))
print(f"list items: {len(data)}")

# Try a few law identifiers from list.json
samples = data[:3]
for i, s in enumerate(samples):
    print(f"\n[{i}] name={s.get('name')!r}  num={s.get('num')!r}")

# e-Gov 法令 API:
#   v1: https://laws.e-gov.go.jp/api/1/lawdata/{lawId}        (lawId or 法令番号)
#   v2: https://laws.e-gov.go.jp/api/2/law_data/{lawId}?...
#   現行(2024-): https://laws.e-gov.go.jp/api/2/...

s = samples[0]
candidates = [
    ("v1 num", f"https://laws.e-gov.go.jp/api/1/lawdata/{urllib.parse.quote(s['num'])}"),
    ("v2 num", f"https://laws.e-gov.go.jp/api/2/lawdata/{urllib.parse.quote(s['num'])}"),
    ("v2 law_data", f"https://laws.e-gov.go.jp/api/2/law_data/{urllib.parse.quote(s['num'])}"),
    ("v1 lawlists", f"https://laws.e-gov.go.jp/api/1/lawlists/1"),
    ("v2 laws", f"https://laws.e-gov.go.jp/api/2/laws?law_num_era=Heisei&limit=1"),
]
for label, url in candidates:
    try:
        r = requests.get(url, timeout=15)
        ct = r.headers.get("Content-Type", "")[:60]
        body_head = r.text[:200].replace("\n", " ")
        print(f"\n[{label}] {r.status_code}  ct={ct}  len={len(r.content)}")
        print(f"    URL: {url}")
        print(f"    body[0:200]: {body_head}")
    except Exception as e:
        print(f"\n[{label}] ERR: {e}")
        print(f"    URL: {url}")
