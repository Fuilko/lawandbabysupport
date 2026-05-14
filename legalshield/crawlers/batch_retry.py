"""Retry datasets that failed in the first pass with broader keywords."""
from __future__ import annotations

from .batch_fetch import fetch_dataset

RETRY: list[tuple[str, str, int, str | None]] = [
    ("prosecution_moj",  "検察統計調査", 30, None),
    ("judicial_courts",  "司法統計年報", 20, None),
    ("special_fraud",    "サイバー", 10, None),
    ("child_abuse",      "児童相談所", 15, None),
    ("consumer_pio",     "消費者相談", 15, None),
    ("labor_dispute",    "個別労働", 10, None),
    ("bullying_mext",    "問題行動", 10, None),
    ("disability_consult","障害者虐待", 10, None),
    ("legal_aid",        "法律扶助", 5, None),
    # Additional priority topics
    ("traffic_acc",      "交通事故", 15, None),
    ("violence_crime",   "暴行", 10, None),
    ("gender_violence",  "ジェンダー", 5, None),
    ("homelessness",     "ホームレス", 5, None),
    ("poverty",          "生活保護", 10, None),
    ("women_workers",    "女性労働", 10, None),
]


def main() -> None:
    summary = []
    for d, kw, n, ag in RETRY:
        try:
            summary.append(fetch_dataset(d, kw, n, ag))
        except Exception as e:  # noqa: BLE001
            summary.append({"dataset": d, "ok": 0, "fail": -1, "planned": 0, "err": str(e)})
    print("\n=== RETRY SUMMARY ===")
    for s in summary:
        print(f"  {s['dataset']:24s}  ok={s['ok']:3d}  fail={s['fail']:3d}  planned={s['planned']}")


if __name__ == "__main__":
    main()
