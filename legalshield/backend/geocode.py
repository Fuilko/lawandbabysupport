"""Offline geocoding for Japanese addresses using jageocoder.

Requires jageocoder dictionary download (one-time, ~1GB).
Processes facility/support-center address lists and outputs lat/lon CSV.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import jageocoder

ROOT = Path(__file__).resolve().parents[1]


def ensure_dict() -> bool:
    try:
        jageocoder.init()
        return True
    except Exception:
        print("[info] downloading jageocoder dictionary (one-time, ~1GB) ...")
        try:
            jageocoder.install_dictionary()
            jageocoder.init()
            return True
        except Exception as e:
            print(f"[error] failed to install dictionary: {e}")
            return False


def geocode_file(csv_path: Path, out_path: Path) -> int:
    if not csv_path.exists():
        print(f"[warn] {csv_path} not found")
        return 0
    rows = []
    with open(csv_path, encoding="utf-8-sig") as f:
        rdr = csv.DictReader(f)
        for row in rdr:
            addr = row.get("address") or row.get("住所") or ""
            if not addr:
                continue
            try:
                result = jageocoder.search(addr)
                if result and result["candidates"]:
                    best = result["candidates"][0]
                    rows.append({
                        **row,
                        "lat": best.get("y"),
                        "lon": best.get("x"),
                        "matched": best.get("matched_string"),
                    })
                else:
                    rows.append({**row, "lat": None, "lon": None, "matched": None})
            except Exception:
                rows.append({**row, "lat": None, "lon": None, "matched": None})

    if rows:
        import pandas as pd
        pd.DataFrame(rows).to_csv(out_path, index=False, encoding="utf-8-sig")
        print(f"[ok] wrote {out_path}  rows={len(rows)}")
    return len(rows)


def geocode_seed_files() -> None:
    seeds = [
        (ROOT / "knowledge" / "seeds" / "ngo_seed.csv",
         ROOT / "knowledge" / "seeds" / "ngo_seed_geocoded.csv"),
    ]
    total = 0
    for inp, out in seeds:
        total += geocode_file(inp, out)
    print(f"\nTOTAL geocoded: {total}")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--file", help="specific CSV to geocode")
    p.add_argument("--out", help="output CSV path")
    args = p.parse_args()

    if not ensure_dict():
        return

    if args.file:
        geocode_file(Path(args.file), Path(args.out))
    else:
        geocode_seed_files()


if __name__ == "__main__":
    main()
