"""Local OCR pipeline: scanned PDF + JPG → text.

100% local processing (no cloud), critical for sensitive case evidence.

Stack:
  - PyMuPDF (fitz): PDF → image (no poppler / no system dep)
  - EasyOCR: image → text (Japanese + Traditional Chinese + English)
  - GPU (CUDA) accelerated on RTX 4080

Usage:
    python scripts/ocr_pipeline.py --pdf "path/to/scan.pdf" --out "out.txt"
    python scripts/ocr_pipeline.py --image "photo.jpg" --out "out.txt"
    python scripts/ocr_pipeline.py --case mapry --evidence-dir "E:\\mapry"
        # batch OCR all scanned PDFs + images in case folder,
        # output to private/<case>/_ocr/
"""
from __future__ import annotations
import argparse
import json
import sys
import time
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

_reader = None


def get_reader(langs=None, gpu: bool = True):
    """Lazy-init EasyOCR reader (heavy: downloads models on first call)."""
    global _reader
    if _reader is None:
        import easyocr
        # EasyOCR: ch_tra is only compatible with 'en' (cannot mix with 'ja').
        # Mapry 案 mostly Japanese, so default to ['ja', 'en'].
        # For Chinese-only documents, re-run with langs=['ch_tra', 'en'].
        langs = langs or ['ja', 'en']
        print(f"[init] loading EasyOCR models (gpu={gpu}, langs={langs})...", file=sys.stderr)
        _reader = easyocr.Reader(langs, gpu=gpu)
    return _reader


def pdf_to_images(pdf_path: Path, dpi: int = 300) -> list[Path]:
    """PDF → list of PNG file paths (in tmp dir)."""
    import fitz
    import tempfile
    out_dir = Path(tempfile.mkdtemp(prefix="pdf_ocr_"))
    imgs = []
    doc = fitz.open(pdf_path)
    for i, page in enumerate(doc):
        pix = page.get_pixmap(dpi=dpi)
        p = out_dir / f"page_{i+1:03d}.png"
        pix.save(str(p))
        imgs.append(p)
    return imgs


def ocr_image(img_path: Path, langs=None, gpu: bool = True) -> str:
    reader = get_reader(langs=langs, gpu=gpu)
    result = reader.readtext(str(img_path), detail=0, paragraph=True)
    return "\n".join(result)


def ocr_pdf(pdf_path: Path, langs=None, gpu: bool = True) -> str:
    """Scan PDF → text (page-by-page)."""
    reader = get_reader(langs=langs, gpu=gpu)
    out_parts = []
    imgs = pdf_to_images(pdf_path)
    for i, img in enumerate(imgs, 1):
        t0 = time.time()
        result = reader.readtext(str(img), detail=0, paragraph=True)
        elapsed = time.time() - t0
        out_parts.append(f"--- page {i} (OCR {elapsed:.1f}s) ---")
        out_parts.append("\n".join(result))
        print(f"  page {i}/{len(imgs)} done in {elapsed:.1f}s "
              f"({sum(len(r) for r in result)} chars)", file=sys.stderr)
    # cleanup
    try:
        for img in imgs:
            img.unlink()
        imgs[0].parent.rmdir()
    except Exception:
        pass
    return "\n".join(out_parts)


# ============================================================================
# Batch case-level OCR
# ============================================================================

def batch_case(case_id: str, evidence_dir: Path, out_dir: Path,
               gpu: bool = True, mark_in_manifest: bool = True) -> dict:
    """Process all unread OCR/vision files in a case folder.

    Reads the evidence_manifest.json, OCRs every file marked needs_ocr=True
    AND read_by_agent=False, saves output to out_dir, and marks read.
    """
    from legalshield.backend import evidence_gate as eg

    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = ROOT / "private" / case_id / "evidence_manifest.json"
    # also try mapry_ai
    if not manifest_path.exists():
        alt = ROOT / "private" / f"{case_id}_ai" / "evidence_manifest.json"
        if alt.exists():
            manifest_path = alt
    if not manifest_path.exists():
        raise SystemExit(f"manifest not found: {manifest_path}")

    manifest = eg.load_manifest(manifest_path)
    targets = [f for f in manifest.files
               if (f.needs_ocr or f.needs_vision) and not f.read_by_agent]
    print(f"[batch] case={case_id}, {len(targets)} files to OCR", file=sys.stderr)

    results = {"processed": [], "skipped": [], "errors": []}
    for i, f in enumerate(targets, 1):
        src = evidence_dir / f.relpath
        if not src.exists():
            results["skipped"].append((f.relpath, "source missing"))
            continue
        safe_name = f.relpath.replace("\\", "_").replace("/", "_") + ".ocr.txt"
        out_path = out_dir / safe_name
        if out_path.exists() and out_path.stat().st_size > 100:
            print(f"[{i}/{len(targets)}] CACHED: {f.relpath}", file=sys.stderr)
            f.read_by_agent = True
            f.notes = (f.notes + " | " if f.notes else "") + "OCR cached"
            results["processed"].append((f.relpath, "cached"))
            continue
        try:
            print(f"[{i}/{len(targets)}] OCR: {f.relpath}", file=sys.stderr)
            t0 = time.time()
            if src.suffix.lower() == ".pdf":
                text = ocr_pdf(src, gpu=gpu)
            else:
                text = ocr_image(src, gpu=gpu)
            out_path.write_text(text, encoding="utf-8")
            elapsed = time.time() - t0
            chars = len(text)
            print(f"  → {chars} chars in {elapsed:.1f}s, saved {out_path.name}",
                  file=sys.stderr)
            f.read_by_agent = True
            f.extracted_chars = chars
            f.notes = (f.notes + " | " if f.notes else "") + f"OCR done ({chars} chars)"
            results["processed"].append((f.relpath, "ok"))
        except Exception as e:
            print(f"  ERR: {e}", file=sys.stderr)
            results["errors"].append((f.relpath, str(e)))

    if mark_in_manifest:
        eg.save_manifest(manifest, manifest_path)
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", help="single PDF input")
    ap.add_argument("--image", help="single image input")
    ap.add_argument("--out", help="output text file")
    ap.add_argument("--case", help="case id for batch mode")
    ap.add_argument("--evidence-dir", help="source evidence dir for --case")
    ap.add_argument("--out-dir", help="output dir for --case mode")
    ap.add_argument("--no-gpu", action="store_true")
    args = ap.parse_args()

    gpu = not args.no_gpu

    if args.case:
        evd = Path(args.evidence_dir or r"E:\mapry")
        out = Path(args.out_dir or ROOT / "private" / f"{args.case}_ai" / "_ocr")
        results = batch_case(args.case, evd, out, gpu=gpu)
        print(f"\n=== batch result ===")
        print(f"processed: {len(results['processed'])}")
        print(f"skipped:   {len(results['skipped'])}")
        print(f"errors:    {len(results['errors'])}")
        for path, why in results["errors"][:5]:
            print(f"  ERR: {path}  ({why})")
        return

    if args.pdf:
        text = ocr_pdf(Path(args.pdf), gpu=gpu)
    elif args.image:
        text = ocr_image(Path(args.image), gpu=gpu)
    else:
        ap.error("--pdf, --image, or --case required")

    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"\nsaved to {args.out}")
    else:
        print(text)


if __name__ == "__main__":
    main()
