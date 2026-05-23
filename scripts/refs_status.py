import json
from pathlib import Path
m = json.loads(Path(r"D:\projects\LegalShield\docs\refs\manifest.json").read_text(encoding="utf-8"))
print(f"=== Failed ({sum(1 for r in m if not r.get('ok'))}) ===")
for r in m:
    if not r.get("ok"):
        err = (r.get("error") or "")[:60]
        print(f"  {r['key']:40s} HTTP={r.get('http','?')}  {err}")
print(f"\n=== Success summary ===")
ok = [r for r in m if r.get("ok")]
total_size = sum(r.get("size", 0) for r in ok)
print(f"  main ok: {len(ok)}, total size: {total_size/1e6:.2f} MB")
sub = [s for r in m for s in r.get("sub_assets", []) if s.get("ok")]
sub_size = sum(s.get("size", 0) for s in sub)
print(f"  sub-assets ok: {len(sub)}, total size: {sub_size/1e6:.2f} MB")
print(f"  GRAND TOTAL: {(total_size+sub_size)/1e6:.2f} MB across {len(ok)+len(sub)} files")
