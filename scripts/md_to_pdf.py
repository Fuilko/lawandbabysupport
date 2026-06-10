"""Markdown → HTML → PDF (Edge headless) with print-friendly CSS, TOC, page-breaks.

v1.2 (2026-06-09):
- Generates a persistent HTML file alongside the PDF (for inspection/print).
- Auto TOC (Table of Contents) at depth 2-4.
- @page rule with footer page numbers.
- @media print rules for table no-break / heading-no-orphan / pre-no-break.
- Edge headless print to PDF with retry & user-data-dir isolation.

Usage:
    python scripts/md_to_pdf.py <input.md> [output.pdf]
    python scripts/md_to_pdf.py --all
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import markdown as md

ROOT = Path(__file__).resolve().parents[1]
MAPRY_DIR = ROOT / "private" / "mapry_ai"

EDGE_PATHS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]

CSS = r"""
@page {
  size: A4;
  margin: 18mm 16mm 22mm 16mm;
  @bottom-center {
    content: "— " counter(page) " / " counter(pages) " —";
    font-size: 9pt;
    color: #888;
  }
}
@media print {
  table { page-break-inside: auto; }
  tr    { page-break-inside: avoid; page-break-after: auto; }
  thead { display: table-header-group; }
  tfoot { display: table-footer-group; }
  h1, h2, h3 { page-break-after: avoid; }
  pre, blockquote { page-break-inside: avoid; }
}
* { box-sizing: border-box; }
html, body {
  font-family: "Yu Gothic UI", "Yu Gothic", "Hiragino Sans", "Hiragino Kaku Gothic ProN",
               "Microsoft YaHei", "微軟正黑體", "Noto Sans CJK JP", sans-serif;
  font-size: 10.5pt;
  line-height: 1.65;
  color: #1a1a1a;
}
body { margin: 0; padding: 0; }
h1 {
  font-size: 22pt;
  color: #142d52;
  border-bottom: 3px solid #142d52;
  padding-bottom: 6mm;
  margin: 0 0 8mm 0;
  page-break-before: always;
}
h1:first-of-type { page-break-before: avoid; }
h2 {
  font-size: 15pt;
  color: #2c4a7e;
  border-left: 5px solid #2c4a7e;
  padding-left: 10px;
  margin: 10mm 0 4mm 0;
}
h3 { font-size: 12.5pt; color: #444; margin: 6mm 0 2mm 0; font-weight: 700; }
h4 { font-size: 11.5pt; color: #555; margin: 4mm 0 1.5mm 0; font-weight: 700; }
p { margin: 0 0 2.5mm 0; }
ul, ol { margin: 0 0 3mm 0; padding-left: 22px; }
li { margin-bottom: 0.8mm; }
strong { color: #c0392b; font-weight: 700; }
em { color: #6b4500; font-style: normal; background: #fff3c0; padding: 0 3px; border-radius: 2px; }
code {
  background: #f4f4f4; border: 1px solid #ddd; border-radius: 3px;
  padding: 0 5px;
  font-family: "Cascadia Mono", "Consolas", "Yu Gothic UI", monospace;
  font-size: 9.5pt; color: #d33;
}
pre {
  background: #f8f8f8; border-left: 4px solid #2c4a7e;
  padding: 4mm 6mm; font-size: 9pt; line-height: 1.45;
  overflow-x: auto;
}
pre code { background: none; border: 0; padding: 0; color: #333; }
table {
  border-collapse: collapse; width: 100%;
  margin: 3mm 0 4mm 0; font-size: 10pt;
}
th {
  background: #142d52; color: white;
  padding: 2mm 3mm; text-align: left; font-weight: 600;
  border: 1px solid #142d52;
}
td { border: 1px solid #ccc; padding: 1.8mm 3mm; vertical-align: top; }
tr:nth-child(even) { background: #f7f9fc; }
blockquote {
  border-left: 4px solid #888; background: #fafafa;
  padding: 3mm 5mm; margin: 2mm 0; color: #444; font-size: 10pt;
}
hr { border: 0; border-top: 1px solid #ddd; margin: 6mm 0; }
a { color: #2c4a7e; text-decoration: none; border-bottom: 1px solid #aac; }

.doc-header {
  text-align: center;
  margin: 10mm 0 12mm 0;
  padding: 6mm 0;
  border-top: 2px solid #142d52;
  border-bottom: 2px solid #142d52;
}
.doc-header .title { font-size: 24pt; font-weight: 700; color: #142d52; margin: 0; }
.doc-header .subtitle { font-size: 11pt; color: #666; margin: 3mm 0 0 0; }
.doc-header .meta { font-size: 9pt; color: #888; margin-top: 2mm; }

.footer-mark {
  text-align: center;
  font-size: 8.5pt;
  color: #999;
  border-top: 1px solid #ddd;
  margin-top: 10mm;
  padding-top: 3mm;
  font-style: italic;
}

.toc-section {
  background: #f7f9fc;
  border-left: 5px solid #2c4a7e;
  padding: 6mm 8mm 6mm 6mm;
  margin: 5mm 0 8mm 0;
  page-break-after: always;
}
.toc-section .toctitle {
  font-size: 14pt; font-weight: 700; color: #142d52; margin: 0 0 3mm 0;
}
.toc-section ul { padding-left: 20px; margin: 1mm 0; list-style-type: none; }
.toc-section ul ul { padding-left: 16px; }
.toc-section li { font-size: 10pt; margin-bottom: 0.5mm; }
.toc-section a { color: #2c4a7e; border: none; }

.badge { display: inline-block; padding: 1px 7px; border-radius: 10px; font-size: 9pt; font-weight: 600; color: white; }
.badge-high { background: #c0392b; }
.badge-mid  { background: #e67e22; }
.badge-low  { background: #95a5a6; }
.badge-ok   { background: #27ae60; }
"""


def find_edge() -> str:
    for p in EDGE_PATHS:
        if Path(p).exists():
            return p
    edge = shutil.which("msedge")
    if edge:
        return edge
    raise SystemExit("Microsoft Edge not found.")


def md_to_html(text: str, title: str = "") -> str:
    """Markdown → standalone HTML with TOC & print CSS."""
    extensions = ["tables", "fenced_code", "toc", "sane_lists", "nl2br", "attr_list", "footnotes"]
    md_inst = md.Markdown(extensions=extensions, extension_configs={
        "toc": {"toc_depth": "2-4", "permalink": False, "title": "目次 / Table of Contents"},
    })
    html_body = md_inst.convert(text)
    toc_html = md_inst.toc or ""

    header_html = ""
    if title:
        header_html = f"""
        <div class="doc-header">
          <div class="title">{title}</div>
          <div class="subtitle">Mapry M4-0 ADR 不成立後 戦略パッケージ</div>
          <div class="meta">生成: 2026-06-09 / LegalShield 接地分析（pgvector 550,570 法令 + 724,443 判例）</div>
        </div>
        """

    toc_block = f'<div class="toc-section">{toc_html}</div>' if toc_html else ""

    return f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8" />
<title>{title or 'Mapry case'}</title>
<style>{CSS}</style>
</head>
<body>
{header_html}
{toc_block}
{html_body}
<div class="footer-mark">本書は LegalShield AI 接地分析の補助資料です。法律行動は弁護士の最終判断を要します。</div>
</body>
</html>"""


def render_pdf(md_path: Path, pdf_path: Path, title: str = "") -> tuple:
    """Render md to (HTML kept, PDF). Returns (html_path, pdf_path)."""
    edge = find_edge()
    text = md_path.read_text(encoding="utf-8")
    if not title:
        for line in text.splitlines():
            if line.startswith("# "):
                title = line[2:].strip()
                break
        else:
            title = md_path.stem

    html_str = md_to_html(text, title)

    persistent_html = pdf_path.with_suffix(".html")
    persistent_html.write_text(html_str, encoding="utf-8")
    print(f"  HTML kept: {persistent_html}")

    url = "file:///" + str(persistent_html.resolve()).replace("\\", "/")
    for attempt in range(3):
        if pdf_path.exists():
            try:
                pdf_path.unlink()
            except Exception:
                pass
        user_data = tempfile.mkdtemp(prefix="edge_pdf_")
        cmd = [
            edge,
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            "--no-pdf-header-footer",
            f"--user-data-dir={user_data}",
            f"--print-to-pdf={pdf_path}",
            url,
        ]
        print(f"[render attempt {attempt+1}] {md_path.name} -> {pdf_path.name}")
        # Note: capture_output=False (let Edge log to console) avoids Windows pipe deadlock
        result = subprocess.run(cmd, timeout=300)
        if pdf_path.exists() and pdf_path.stat().st_size > 1024:
            size_kb = pdf_path.stat().st_size / 1024
            print(f"  OK {pdf_path}  ({size_kb:.1f} KB)")
            return persistent_html, pdf_path
        time.sleep(2 + attempt)
    raise SystemExit(f"PDF generation failed for {md_path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", nargs="?")
    ap.add_argument("output", nargs="?")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--dir")
    args = ap.parse_args()

    if args.all:
        targets = sorted(MAPRY_DIR.glob("*_2026-*.md")) + sorted(MAPRY_DIR.glob("MASTER*.md"))
        for extra in ["LEGAL_EVIDENCE_REPORT.md", "CRIMINAL_EVIDENCE_REPORT.md",
                      "ADMIN_CHANNELS_REPORT.md"]:
            p = MAPRY_DIR / extra
            if p.exists() and p not in targets:
                targets.append(p)
        for t in targets:
            try:
                render_pdf(t, t.with_suffix(".pdf"))
            except SystemExit as e:
                print(f"  retry: {e}")
                time.sleep(3)
                render_pdf(t, t.with_suffix(".pdf"))
            time.sleep(1)
        return

    if args.dir:
        d = Path(args.dir)
        for t in sorted(d.glob("*.md")):
            render_pdf(t, t.with_suffix(".pdf"))
        return

    if not args.input:
        ap.error("input or --all required")
    inp = Path(args.input).resolve()
    out = Path(args.output).resolve() if args.output else inp.with_suffix(".pdf")
    render_pdf(inp, out)


if __name__ == "__main__":
    main()
