"""並列ダウンロード: e-Gov 法令 API v1 → XML → knowledge/raw/elaws/lawdata/

list.json (8,790 件) の `num` フィールドを law_id として API を叩く。
BAD_FILENAME 文字 (/, :, etc) を sanitize する。

使い方:
    python scripts/elaws_download.py --workers 8 --sleep 1.0
    # ~18-30 min for 8,790 laws

再開可能: 既に存在し >500 byte のファイルは skip。
"""
from __future__ import annotations

import argparse
import json
import re
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
LIST_JSON = ROOT / "data_set" / "law" / "list.json"
BODY_DIR = ROOT / "legalshield" / "knowledge" / "raw" / "elaws" / "lawdata"
BASE = "https://laws.e-gov.go.jp/api/1/lawdata"

_BAD = re.compile(r"[\\/:*?\"<>|]")


def safe_name(s: str) -> str:
    return _BAD.sub("_", s)


def fetch_one(num: str, sleep_sec: float, session: requests.Session) -> tuple[str, str]:
    """Returns (status, num)."""
    fname = safe_name(num) + ".xml"
    target = BODY_DIR / fname
    if target.exists() and target.stat().st_size > 500:
        return ("cached", num)
    url = f"{BASE}/{urllib.parse.quote(num)}"
    try:
        r = session.get(url, timeout=120)
        r.raise_for_status()
        body = r.content
        if len(body) < 500:
            return ("too_small", num)
        target.write_bytes(body)
        time.sleep(sleep_sec)
        return ("ok", num)
    except Exception as e:
        return (f"fail:{type(e).__name__}", num)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--workers", type=int, default=8)
    p.add_argument("--sleep", type=float, default=1.0)
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--start", type=int, default=0)
    args = p.parse_args()

    BODY_DIR.mkdir(parents=True, exist_ok=True)
    data = json.loads(LIST_JSON.read_text(encoding="utf-8"))
    nums = [d["num"] for d in data if d.get("num")]
    nums = nums[args.start:]
    if args.limit:
        nums = nums[: args.limit]
    print(f"[plan] {len(nums)} laws, {args.workers} workers, sleep={args.sleep}s/worker")

    sess = requests.Session()
    sess.headers["User-Agent"] = "LegalShield/1.0 (+https://github.com/Fuilko/lawandbabysupport)"

    ok = cached = fail = small = 0
    fail_log: list[tuple[str, str]] = []
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(fetch_one, n, args.sleep, sess): n for n in nums}
        for i, fu in enumerate(as_completed(futs), 1):
            status, num = fu.result()
            if status == "ok":
                ok += 1
            elif status == "cached":
                cached += 1
            elif status == "too_small":
                small += 1
            else:
                fail += 1
                fail_log.append((status, num))
            if i % 100 == 0 or i == len(nums):
                el = time.time() - t0
                rate = i / el if el else 0
                eta = (len(nums) - i) / rate if rate else 0
                print(f"[prog] {i}/{len(nums)} ok={ok} cached={cached} fail={fail} small={small}  "
                      f"rate={rate:.1f}/s eta={eta/60:.1f}min")
    el = time.time() - t0
    print(f"[done] ok={ok} cached={cached} fail={fail} small={small}  total={len(nums)}  elapsed={el/60:.1f}min")
    if fail_log:
        log_path = ROOT / "scripts" / "elaws_download_fails.log"
        log_path.write_text("\n".join(f"{s}\t{n}" for s, n in fail_log), encoding="utf-8")
        print(f"[fail] details written to {log_path}")


if __name__ == "__main__":
    main()
