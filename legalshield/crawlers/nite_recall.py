"""NITE (製品評価技術基盤機構) accident & recall data.

NITE publishes 事故情報 search at https://www.nite.go.jp/jiko/index.html
and downloadable CSV at https://www.jikojoho.caa.go.jp/ai-national/ (消費者庁).

For PoC we pull the consumer-affairs CSV which is the most structured.
"""
from __future__ import annotations

import argparse

from .common import download, log

CAA_RECALL_INDEX = "https://www.recall.caa.go.jp/result/index.php"
CAA_OPEN_DATA = "https://www.caa.go.jp/policies/policy/consumer_safety/release/"


def fetch_index() -> None:
    download(CAA_RECALL_INDEX, source="caa_recall", filename="index.html",
             note="consumer-affairs recall search page")
    download(CAA_OPEN_DATA, source="caa_recall", filename="open_data.html",
             note="consumer-affairs open data index")
    log.info("indexes saved; manual inspection of links recommended for PoC")


def main() -> None:
    p = argparse.ArgumentParser(description="NITE / 消費者庁 recall")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("fetch-index")
    args = p.parse_args()
    if args.cmd == "fetch-index":
        fetch_index()


if __name__ == "__main__":
    main()
