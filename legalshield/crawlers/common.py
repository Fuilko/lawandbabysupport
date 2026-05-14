"""Common utilities for all crawlers.

- Path layout (raw / parsed)
- HTTP session with retries + UA
- SHA256 chain of custody for raw downloads
- Parquet writer
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]                  # legalshield/
KNOWLEDGE = ROOT / "knowledge"
RAW = KNOWLEDGE / "raw"
PARSED = KNOWLEDGE / "parsed"
DUCKDB_PATH = KNOWLEDGE / "unified.duckdb"
MANIFEST = KNOWLEDGE / "manifest.jsonl"

for p in (RAW, PARSED):
    p.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=os.environ.get("LEGALSHIELD_LOG", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("crawlers")

# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------
_UA = (
    "LegalShield/0.1 (+https://github.com/Fuilko/lawandbabysupport) "
    "research-crawler contact: legalshield@example.jp"
)


def session() -> requests.Session:
    s = requests.Session()
    retry = Retry(
        total=5,
        backoff_factor=1.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET", "HEAD"),
    )
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.mount("http://", HTTPAdapter(max_retries=retry))
    s.headers.update({"User-Agent": _UA, "Accept-Language": "ja,en;q=0.7"})
    return s


# ---------------------------------------------------------------------------
# Manifest / chain of custody
# ---------------------------------------------------------------------------
@dataclass
class ManifestEntry:
    source: str
    url: str
    saved_to: str
    sha256: str
    bytes: int
    fetched_at: str            # ISO8601 UTC
    content_type: str | None = None
    note: str | None = None


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def append_manifest(entry: ManifestEntry) -> None:
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST, "a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(entry), ensure_ascii=False) + "\n")


def download(
    url: str,
    source: str,
    subdir: str = "",
    filename: str | None = None,
    sleep_sec: float = 1.0,
    note: str | None = None,
) -> Path:
    """Download `url` to RAW/source/subdir/filename and append to manifest.

    Idempotent: if the target file already exists, returns it without re-download.
    """
    target_dir = RAW / source / subdir
    target_dir.mkdir(parents=True, exist_ok=True)
    name = filename or url.rstrip("/").split("/")[-1] or "index.html"
    out = target_dir / name

    if out.exists() and out.stat().st_size > 0:
        log.info("cached: %s", out)
        return out

    log.info("GET %s", url)
    with session() as s:
        r = s.get(url, timeout=60, stream=True)
        r.raise_for_status()
        ct = r.headers.get("Content-Type")
        with open(out, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 16):
                if chunk:
                    f.write(chunk)
    time.sleep(sleep_sec)

    entry = ManifestEntry(
        source=source,
        url=url,
        saved_to=str(out.relative_to(ROOT)),
        sha256=sha256_file(out),
        bytes=out.stat().st_size,
        fetched_at=datetime.now(timezone.utc).isoformat(),
        content_type=ct,
        note=note,
    )
    append_manifest(entry)
    return out


# ---------------------------------------------------------------------------
# Parquet writer (lazy import to keep base deps light)
# ---------------------------------------------------------------------------
def write_parquet(rows: Iterable[dict], dataset: str, partition: str | None = None) -> Path:
    import pandas as pd

    df = pd.DataFrame(list(rows))
    if df.empty:
        log.warning("write_parquet: empty dataset %s", dataset)
    target_dir = PARSED / dataset
    target_dir.mkdir(parents=True, exist_ok=True)
    fname = f"{partition or datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.parquet"
    out = target_dir / fname
    df.to_parquet(out, index=False)
    log.info("wrote %s rows=%d cols=%s", out, len(df), list(df.columns))
    return out
