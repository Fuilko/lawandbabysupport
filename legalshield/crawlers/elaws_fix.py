"""Re-download e-LAWS XML files that were saved as HTML error pages.

Scans knowledge/raw/elaws/lawdata/, identifies HTML files,
re-fetches them sequentially, and overwrites with correct XML.
"""
from __future__ import annotations

import time
from pathlib import Path

from .common import log, session

RAW_DIR = Path(__file__).resolve().parents[1] / "knowledge" / "raw" / "elaws" / "lawdata"
BASE = "https://laws.e-gov.go.jp/api/1/lawdata"


def is_html(path: Path) -> bool:
    try:
        with open(path, "rb") as f:
            header = f.read(200)
        return b"<!DOCTYPE html" in header or b"<html" in header
    except Exception:
        return True


def fix_all(sleep_sec: float = 0.5) -> dict:
    files = sorted(RAW_DIR.glob("*.xml"))
    html_files = [f for f in files if is_html(f)]
    log.info("found %d HTML files out of %d total", len(html_files), len(files))

    ok = fail = 0
    for i, f in enumerate(html_files, 1):
        law_id = f.stem
        url = f"{BASE}/{law_id}"
        try:
            with session() as s:
                r = s.get(url, timeout=60)
                r.raise_for_status()
                # Verify it's XML not HTML
                if b"<!DOCTYPE html" in r.content[:200] or b"<html" in r.content[:200]:
                    log.debug("still HTML for %s", law_id)
                    fail += 1
                    continue
                with open(f, "wb") as out:
                    out.write(r.content)
                ok += 1
        except Exception as e:  # noqa: BLE001
            log.debug("fail %s: %s", law_id, e)
            fail += 1
        if i % 100 == 0:
            log.info("progress %d/%d  ok=%d fail=%d", i, len(html_files), ok, fail)
        time.sleep(sleep_sec)

    log.info("DONE ok=%d fail=%d  total=%d", ok, fail, len(html_files))
    return {"ok": ok, "fail": fail, "total": len(html_files)}


def main() -> None:
    stats = fix_all()
    print(f"\nFixed: {stats['ok']}  Still failed: {stats['fail']}")


if __name__ == "__main__":
    main()
