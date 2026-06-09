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


def _is_real_xml(body: bytes) -> bool:
    """Reject e-Gov 'page not found' HTML pages that come back with 200 status."""
    head = body[:200].lstrip()
    return head.startswith(b"<?xml")


def fetch_one(num: str, sleep_sec: float, session: requests.Session,
              max_retries: int = 3) -> tuple[str, str]:
    """Returns (status, num). Validates body is real XML, not HTML 404 page.
    Retries with exponential backoff when rate-limited (HTML response on 200)."""
    fname = safe_name(num) + ".xml"
    target = BODY_DIR / fname
    if target.exists() and target.stat().st_size > 500:
        # Re-validate cached files to skip HTML 404 leftover
        try:
            with open(target, "rb") as f:
                h = f.read(200)
            if h.lstrip().startswith(b"<?xml"):
                return ("cached", num)
        except Exception:
            pass
    url = f"{BASE}/{urllib.parse.quote(num)}"
    backoff = sleep_sec
    for attempt in range(max_retries):
        try:
            r = session.get(url, timeout=120)
            if r.status_code == 404:
                time.sleep(sleep_sec)
                return ("not_found", num)
            r.raise_for_status()
            body = r.content
            if not _is_real_xml(body):
                # Rate-limited: e-Gov returned HTML "page not found" with 200
                time.sleep(backoff * 2)
                backoff *= 2
                continue
            if len(body) < 200:
                return ("too_small", num)
            target.write_bytes(body)
            time.sleep(sleep_sec)
            return ("ok", num)
        except Exception as e:
            time.sleep(backoff)
            backoff *= 2
            if attempt == max_retries - 1:
                return (f"fail:{type(e).__name__}", num)
    return ("rate_limited", num)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--workers", type=int, default=3,
                   help="本数<=4 推奨。多すぎると e-Gov に 200+HTML を返される")
    p.add_argument("--sleep", type=float, default=2.0,
                   help="per-worker pause; 効果は workers x sleep^-1 req/s")
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

    ok = cached = fail = small = notfound = rl = 0
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
            elif status == "not_found":
                notfound += 1
            elif status == "rate_limited":
                rl += 1
                fail_log.append((status, num))
            else:
                fail += 1
                fail_log.append((status, num))
            if i % 100 == 0 or i == len(nums):
                el = time.time() - t0
                rate = i / el if el else 0
                eta = (len(nums) - i) / rate if rate else 0
                print(f"[prog] {i}/{len(nums)} ok={ok} cached={cached} 404={notfound} "
                      f"rl={rl} fail={fail}  rate={rate:.1f}/s eta={eta/60:.1f}min")
    el = time.time() - t0
    print(f"[done] ok={ok} cached={cached} 404={notfound} rl={rl} fail={fail} "
          f"small={small}  total={len(nums)}  elapsed={el/60:.1f}min")
    if fail_log:
        log_path = ROOT / "scripts" / "elaws_download_fails.log"
        log_path.write_text("\n".join(f"{s}\t{n}" for s, n in fail_log), encoding="utf-8")
        print(f"[fail] details written to {log_path}")


if __name__ == "__main__":
    main()
