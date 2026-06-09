"""Inspect e-Gov v2 law_data JSON structure to figure out how to parse articles."""
import json, urllib.parse, requests, sys
from pathlib import Path

LIST = Path(r"D:\projects\LegalShield\data_set\law\list.json")
data = json.loads(LIST.read_text(encoding="utf-8"))

# Test 5 laws from different eras
sample_indices = [0, 100, 1000, 5000, 8000]
for idx in sample_indices:
    s = data[idx]
    num = s["num"]
    print(f"\n========== [{idx}] name={s.get('name')!r}  num={num!r} ==========")
    # v1 first
    try:
        r1 = requests.get(f"https://laws.e-gov.go.jp/api/1/lawdata/{urllib.parse.quote(num)}", timeout=20)
        body1 = r1.text[:200].replace("\n", " ")
        is_html = body1.lstrip().startswith("<!DOCTYPE")
        print(f"  v1: {r1.status_code}  ct={r1.headers.get('Content-Type','')[:40]}  len={len(r1.content)}  html={is_html}")
    except Exception as e:
        print(f"  v1: ERR {e}")
    # v2
    try:
        r2 = requests.get(f"https://laws.e-gov.go.jp/api/2/law_data/{urllib.parse.quote(num)}", timeout=20)
        print(f"  v2: {r2.status_code}  ct={r2.headers.get('Content-Type','')[:40]}  len={len(r2.content)}")
        if r2.status_code == 200:
            j = r2.json()
            print(f"  v2 top-keys: {list(j.keys())}")
            li = j.get("law_info", {})
            print(f"  v2 law_info keys: {list(li.keys())}")
            # Look for body/article structure
            for k in ["law_full_text", "body", "law_body", "article", "articles", "main_provision"]:
                if k in j:
                    v = j[k]
                    head = json.dumps(v, ensure_ascii=False)[:300] if not isinstance(v, str) else v[:300]
                    print(f"  v2[{k}] head: {head}")
                    break
            # If no obvious key, print all keys recursively at depth 1
            for k, v in j.items():
                if k in ("law_info", "attached_files_info"):
                    continue
                t = type(v).__name__
                size = len(v) if hasattr(v, "__len__") else "?"
                print(f"  v2[{k}]: type={t} size={size}")
    except Exception as e:
        print(f"  v2: ERR {e}")
