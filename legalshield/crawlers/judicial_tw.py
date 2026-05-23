"""
台湾司法院裁判書取得モジュール

API 仕様: docs/judicial_api_spec.pdf (114.08.22 版)
  - Auth:  POST https://data.judicial.gov.tw/jdg/api/Auth
  - JList: POST https://data.judicial.gov.tw/jdg/api/JList   (7日異動)
  - JDoc:  POST https://data.judicial.gov.tw/jdg/api/JDoc    (本文)
  - 提供時間: 毎日 0:00-6:00 (台北時間) のみ
  - 要事前帳号: https://opendata.judicial.gov.tw/ で登録

使用前:
  1. opendata.judicial.gov.tw でアカウント登録
  2. 環境変数に資格情報設定:
       $env:TW_JUDICIAL_USER  = "your_user"
       $env:TW_JUDICIAL_PASS  = "your_pass"
  3. python -m legalshield.crawlers.judicial_tw --days 1 --limit 10

著作権: 台灣著作権法第9条により判決書は公共領域 (no copyright)
個資: 司法院側で自動匿名化済 (二次NER処理は別モジュール)
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Iterable, Iterator, Optional

import requests

logger = logging.getLogger("judicial_tw")

API_BASE = "https://data.judicial.gov.tw/jdg/api"
DEFAULT_OUT = Path(__file__).resolve().parents[1] / "knowledge" / "raw" / "tw_judicial"

# Mapry 案 + LegalShield コア機能に直結する優先キーワード
PRIORITY_KEYWORDS = [
    "代理商", "經銷契約", "終止", "損害賠償",
    "政府採購法", "不良廠商", "停權",
    "瑕疵", "不完全給付", "進口商",
    "詐欺", "不實表示",
    "跟蹤騷擾", "性騷擾",
    "個人資料保護法",
    "兒少", "家庭暴力", "妨害秘密",
    "所失利益", "預期利益",
]

# サービス提供時間 (台北 = UTC+8): 0-6時のみ
SERVICE_HOURS = range(0, 6)


class JudicialAPIError(Exception):
    """司法院 API 呼出失敗"""


@dataclass
class Credentials:
    user: str
    password: str

    @classmethod
    def from_env(cls) -> "Credentials":
        u = os.environ.get("TW_JUDICIAL_USER")
        p = os.environ.get("TW_JUDICIAL_PASS")
        if not u or not p:
            raise JudicialAPIError(
                "TW_JUDICIAL_USER / TW_JUDICIAL_PASS 環境変数が未設定です。"
                "opendata.judicial.gov.tw でアカウント登録してください。"
            )
        return cls(user=u, password=p)


class JudicialClient:
    """司法院裁判書 API クライアント"""

    def __init__(
        self,
        credentials: Credentials,
        session: Optional[requests.Session] = None,
        timeout: int = 60,
        retry: int = 3,
        retry_wait: float = 5.0,
    ):
        self.creds = credentials
        self.session = session or requests.Session()
        self.timeout = timeout
        self.retry = retry
        self.retry_wait = retry_wait
        self._token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None

    # ---------- low-level ----------

    def _post(self, path: str, body: dict) -> dict:
        url = f"{API_BASE}/{path}"
        last_err: Optional[Exception] = None
        for attempt in range(1, self.retry + 1):
            try:
                resp = self.session.post(
                    url,
                    json=body,
                    headers={"Content-Type": "application/json"},
                    timeout=self.timeout,
                )
                resp.raise_for_status()
                data = resp.json()
                if isinstance(data, dict) and data.get("error"):
                    raise JudicialAPIError(f"API error: {data['error']}")
                return data
            except (requests.RequestException, JudicialAPIError, ValueError) as e:
                last_err = e
                logger.warning("attempt %d/%d failed: %s", attempt, self.retry, e)
                time.sleep(self.retry_wait * attempt)
        raise JudicialAPIError(f"{path} failed after {self.retry} retries: {last_err}")

    # ---------- auth ----------

    def authenticate(self, force: bool = False) -> str:
        """Token 取得 (6時間有効)。force=True で再取得。"""
        if (
            not force
            and self._token
            and self._token_expires_at
            and datetime.now(timezone.utc) < self._token_expires_at - timedelta(minutes=5)
        ):
            return self._token
        data = self._post("Auth", {"user": self.creds.user, "password": self.creds.password})
        token = data.get("Token")
        if not token:
            raise JudicialAPIError(f"Token not found in response: {data}")
        self._token = token
        self._token_expires_at = datetime.now(timezone.utc) + timedelta(hours=6)
        logger.info("authenticated; token valid until %s", self._token_expires_at.isoformat())
        return token

    # ---------- list / doc ----------

    def list_recent(self) -> list[dict]:
        """直近 7 日間の異動裁判書 ID リスト。

        Returns:
            [{"date": "YYYY-MM-DD", "list": ["JID1", "JID2", ...]}, ...]
        """
        token = self.authenticate()
        return self._post("JList", {"token": token})

    def get_document(self, jid: str) -> dict:
        """jid から裁判書全文を取得。"""
        token = self.authenticate()
        return self._post("JDoc", {"token": token, "j": jid})


# ---------- 高レベル: 取得 + 保存 ----------


def _within_service_hours(now: Optional[datetime] = None) -> bool:
    """台北時間 0:00-6:00 内か。"""
    now = now or datetime.now(timezone.utc)
    taipei = now + timedelta(hours=8)  # UTC+8
    return taipei.hour in SERVICE_HOURS


def _has_priority_keyword(doc: dict, keywords: Iterable[str]) -> bool:
    """裁判書全文に優先キーワードが含まれるか。"""
    full = (doc.get("JFULLX") or {}).get("JFULLCONTENT") or ""
    title = doc.get("JTITLE") or ""
    haystack = full + " " + title
    return any(kw in haystack for kw in keywords)


def iter_jids(client: JudicialClient, days_back: int = 7) -> Iterator[tuple[str, str]]:
    """異動清單から (date, jid) を順次 yield。

    Args:
        days_back: 過去何日分まで対象とするか (API は最大 7 日)
    """
    days_back = min(days_back, 7)
    cutoff = (datetime.now(timezone.utc) + timedelta(hours=8)).date() - timedelta(days=days_back)
    for entry in client.list_recent():
        date_str = entry.get("date")
        jids = entry.get("list", []) or []
        try:
            entry_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except (TypeError, ValueError):
            logger.warning("invalid date in JList: %r", date_str)
            continue
        if entry_date < cutoff:
            continue
        for jid in jids:
            yield date_str, jid


def harvest(
    out_dir: Path = DEFAULT_OUT,
    days_back: int = 1,
    limit: Optional[int] = None,
    keyword_filter: Optional[Iterable[str]] = PRIORITY_KEYWORDS,
    sleep_sec: float = 1.0,
    enforce_service_hours: bool = True,
) -> dict:
    """直近の裁判書を取得し JSONL に保存。

    Args:
        out_dir: 出力先ディレクトリ
        days_back: 取得対象日数 (1-7)
        limit: 取得件数上限 (None=無制限)
        keyword_filter: フィルタするキーワード (None で全件)
        sleep_sec: 1件ごとの待機 (鯖負荷配慮)
        enforce_service_hours: True なら 0-6 時以外は中止
    """
    if enforce_service_hours and not _within_service_hours():
        raise RuntimeError(
            "司法院 API は台北時間 0:00-6:00 のみ提供。"
            "テスト用に強制実行する場合は enforce_service_hours=False。"
        )

    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = out_dir / f"judgments_{ts}.jsonl"
    stats_path = out_dir / f"stats_{ts}.json"

    client = JudicialClient(Credentials.from_env())
    stats = {
        "started_at": ts,
        "days_back": days_back,
        "limit": limit,
        "keyword_filter": list(keyword_filter) if keyword_filter else None,
        "seen": 0,
        "kept": 0,
        "errors": 0,
        "out_file": str(out_path),
    }

    with out_path.open("w", encoding="utf-8") as f:
        for date_str, jid in iter_jids(client, days_back=days_back):
            stats["seen"] += 1
            if limit and stats["kept"] >= limit:
                break
            try:
                doc = client.get_document(jid)
            except JudicialAPIError as e:
                stats["errors"] += 1
                logger.warning("get_document failed for %s: %s", jid, e)
                time.sleep(sleep_sec)
                continue
            if keyword_filter and not _has_priority_keyword(doc, keyword_filter):
                time.sleep(sleep_sec)
                continue
            record = {
                "country": "TW",
                "source": "judicial.gov.tw",
                "harvested_at": ts,
                "list_date": date_str,
                "jid": jid,
                "doc": doc,
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            stats["kept"] += 1
            time.sleep(sleep_sec)

    stats["finished_at"] = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    stats_path.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(
        "harvest done: seen=%d kept=%d errors=%d out=%s",
        stats["seen"], stats["kept"], stats["errors"], out_path,
    )
    return stats


# ---------- CLI ----------


def _main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="台湾司法院裁判書ハーベスタ")
    parser.add_argument("--days", type=int, default=1, help="過去何日分 (1-7)")
    parser.add_argument("--limit", type=int, default=None, help="取得件数上限")
    parser.add_argument("--no-filter", action="store_true", help="キーワードフィルタ無効化")
    parser.add_argument("--sleep", type=float, default=1.0, help="件間 sleep 秒")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="出力ディレクトリ")
    parser.add_argument(
        "--force",
        action="store_true",
        help="サービス時間外でも実行 (テスト用、API は失敗するかも)",
    )
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    try:
        stats = harvest(
            out_dir=args.out,
            days_back=args.days,
            limit=args.limit,
            keyword_filter=None if args.no_filter else PRIORITY_KEYWORDS,
            sleep_sec=args.sleep,
            enforce_service_hours=not args.force,
        )
    except (JudicialAPIError, RuntimeError) as e:
        logger.error("harvest failed: %s", e)
        return 2
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(_main())
