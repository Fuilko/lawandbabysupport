"""Extract text from RISTEX grant PDFs for analysis."""
from pathlib import Path
from pypdf import PdfReader

BASE = Path(r"D:\projects\LegalShield\docs\grants\ristex_solve_2026")
PDFS = [
    "guideline_common2026_jp.pdf",
    "guideline_solve2026_jp.pdf",
    "guideline_e-rad2026_jp.pdf",
    "faq_solve2026.pdf",
    "faq_common2026.pdf",
]

for f in PDFS:
    src = BASE / f
    if not src.exists():
        continue
    r = PdfReader(str(src))
    out = BASE / (src.stem + ".txt")
    parts = [f"# {f} — {len(r.pages)} pages\n"]
    for i, p in enumerate(r.pages):
        parts.append(f"\n========== page {i+1} ==========\n")
        try:
            parts.append(p.extract_text() or "")
        except Exception as e:
            parts.append(f"[extract error: {e}]")
    out.write_text("".join(parts), encoding="utf-8")
    print(f"{f}: {len(r.pages)} pages -> {out.name} ({out.stat().st_size} bytes)")
