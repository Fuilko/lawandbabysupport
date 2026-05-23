"""
準備書面 TXT -> HTML -> PDF レンダラー
======================================

Mapry 案件用に生成された準備書面 TXT を、日本の法律文書として体裁の整った
HTML に変換し、Microsoft Edge の headless モードで PDF 化する。

出力:
  - private/mapry_ai/drafts/<basename>.html
  - private/mapry_ai/drafts/<basename>.pdf

使い方:
  python private/mapry_ai/training/render_brief_to_pdf.py
"""
from __future__ import annotations

import html
import os
import shutil
import subprocess
import sys
import io
from pathlib import Path

if sys.platform.startswith("win"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parents[3]
DRAFTS_DIR = REPO_ROOT / "private" / "mapry_ai" / "drafts"


CSS = """
@page {
  size: A4;
  margin: 25mm 22mm 25mm 22mm;
}
* { box-sizing: border-box; }
html, body {
  font-family: "Yu Mincho", "游明朝", "MS Mincho", "ＭＳ 明朝", "Hiragino Mincho ProN", serif;
  font-size: 11pt;
  line-height: 1.85;
  color: #111;
  background: #f5f5f5;
}
body { margin: 0; padding: 24px; }
.sheet {
  max-width: 200mm;
  margin: 0 auto;
  background: white;
  padding: 24mm 22mm 26mm 22mm;
  box-shadow: 0 2px 14px rgba(0,0,0,0.08);
  border: 1px solid #e3e3e3;
}
.case-header { font-size: 11pt; margin-bottom: 4mm; }
.case-header .case-no { font-weight: 600; }
.title {
  text-align: center;
  font-size: 18pt;
  font-weight: 700;
  letter-spacing: 0.8em;
  padding-left: 0.8em;
  margin: 10mm 0 8mm 0;
}
.meta {
  display: flex; justify-content: space-between;
  font-size: 10.5pt;
  margin-bottom: 6mm;
}
.meta .right { text-align: right; }
.meta .contact { color: #444; font-size: 10pt; margin-top: 2mm; }
hr.divider {
  border: 0;
  border-top: 1px solid #888;
  margin: 6mm 0;
}
.section-head {
  font-weight: 700;
  font-size: 12.5pt;
  margin: 7mm 0 3mm 0;
  border-left: 4px solid #2c4a7e;
  padding-left: 8px;
  color: #142d52;
}
p { margin: 0 0 3mm 0; text-indent: 1em; }
p.no-indent { text-indent: 0; }
ol, ul { margin: 0 0 3mm 0; padding-left: 28px; }
ol li, ul li { margin-bottom: 1mm; }
.placeholder {
  background: #fff3c0;
  border-radius: 3px;
  padding: 0 4px;
  color: #6b4500;
  font-weight: 600;
}
.law-cite {
  color: #2c4a7e;
  font-weight: 500;
}
.signature-block {
  text-align: right;
  margin: 6mm 0;
  font-size: 11.5pt;
}
.signature-block .seal {
  display: inline-block;
  width: 18mm; height: 18mm;
  border: 2px solid #c0392b;
  border-radius: 50%;
  color: #c0392b;
  font-size: 9pt;
  line-height: 1.1;
  text-align: center;
  padding-top: 6mm;
  margin-left: 6mm;
  vertical-align: middle;
}
.end-mark {
  text-align: right;
  font-weight: 700;
  letter-spacing: 0.5em;
  margin-top: 6mm;
  font-size: 12pt;
}
.attach {
  background: #f7f7f7;
  border-left: 4px solid #888;
  padding: 4mm 6mm;
  font-size: 10.5pt;
  margin-top: 6mm;
}
.attach .head { font-weight: 700; color: #333; margin-bottom: 2mm; }
.watermark-note {
  text-align: center;
  font-size: 9pt;
  color: #888;
  margin-top: 6mm;
  font-style: italic;
}
"""


def txt_to_html(txt: str) -> str:
    """Convert the structured 準備書面 TXT into rich HTML."""
    lines = txt.splitlines()
    out: list[str] = []

    # Heuristic regions
    # 1. First 3 lines = case header (case_no, applicant, respondent)
    # 2. Then '準　備　書　面（第１）'
    # 3. Date
    # 4. Court name
    # 5. Signature line with name + 印
    # 6. Contact lines
    # 7. ─── divider
    # 8. Sections starting with '第' followed by sections / numbered items
    # 9. Final '以　上'
    # 10. '【添付・別紙】' block

    i = 0
    n = len(lines)

    # Skip leading empty lines
    while i < n and not lines[i].strip():
        i += 1

    # Section 1: case header
    out.append('<div class="case-header">')
    while i < n and lines[i].strip() and not lines[i].startswith("準"):
        out.append(f'  <div>{html.escape(lines[i])}</div>')
        i += 1
    out.append("</div>")

    # Title line(s)
    if i < n and lines[i].strip().startswith("準"):
        out.append(f'<div class="title">{html.escape(lines[i].strip())}</div>')
        i += 1

    # Skip blanks
    while i < n and not lines[i].strip():
        i += 1

    # Date + court + signature block (next ~6 non-empty lines)
    meta_lines: list[str] = []
    while i < n and meta_lines.__len__() < 8:
        ln = lines[i].rstrip()
        if not ln.strip():
            i += 1
            continue
        if "────" in ln:
            break
        meta_lines.append(ln)
        i += 1

    if meta_lines:
        out.append('<div class="meta"><div>')
        for ml in meta_lines:
            if "印" in ml:
                # signature line — render special block
                out.append("</div></div>")
                out.append(
                    f'<div class="signature-block">{html.escape(ml.replace("印","").rstrip())}'
                    f'<span class="seal">劉<br>建志</span></div>'
                )
                out.append('<div class="meta"><div>')
            elif "連絡先" in ml or "@" in ml or "Tel" in ml or ml.startswith("０") or ml[:3].isdigit():
                out.append(f'<div class="contact">{html.escape(ml)}</div>')
            else:
                out.append(f'<div>{html.escape(ml)}</div>')
        out.append("</div></div>")

    # Divider then sections
    out.append('<hr class="divider" />')

    # Body sections
    body_buf: list[str] = []
    in_attach = False
    while i < n:
        ln = lines[i]
        stripped = ln.strip()
        if "────" in ln:
            i += 1
            continue
        if stripped == "以　上" or stripped == "以上":
            body_buf.append('<div class="end-mark">以　上</div>')
            i += 1
            continue
        if stripped.startswith("【添付") or stripped.startswith("【別紙"):
            body_buf.append('<div class="attach"><div class="head">' + html.escape(stripped) + '</div>')
            in_attach = True
            i += 1
            continue
        if in_attach:
            if stripped.startswith("　・") or stripped.startswith("・"):
                body_buf.append('<div>' + html.escape(stripped) + '</div>')
            elif not stripped:
                pass
            else:
                body_buf.append('<div>' + html.escape(stripped) + '</div>')
            i += 1
            continue
        if stripped.startswith("第") and "　" in stripped[:6]:
            # Section heading
            body_buf.append(f'<h2 class="section-head">{html.escape(stripped)}</h2>')
            i += 1
            continue
        if not stripped:
            i += 1
            continue
        # Highlight placeholders
        escaped = html.escape(ln.rstrip())
        # placeholder pattern: [...] or 令和●年●月  or ●●●●
        import re
        escaped = re.sub(r"(\[[^\]]+\])", r'<span class="placeholder">\1</span>', escaped)
        escaped = re.sub(r"(令和●年●月●日|令和●年●月|●●●●|●●●|●●)", r'<span class="placeholder">\1</span>', escaped)
        # highlight law citations
        escaped = re.sub(r"(民法\s*\d+\s*条[^）)]*[）)]?|民事訴訟法\s*\d+\s*条|消費者契約法\s*\d+\s*条[^）)]*[）)]?)", r'<span class="law-cite">\1</span>', escaped)
        body_buf.append(f'<p class="no-indent">{escaped}</p>')
        i += 1

    if in_attach:
        body_buf.append('</div>')

    out.extend(body_buf)
    out.append('<div class="watermark-note">⚠ 本書面は AI 補助によるドラフトです。提出前に弁護士の最終確認を必須とします。</div>')

    body_html = "\n".join(out)
    return f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8" />
<title>準備書面（第１） - Mapry 案件</title>
<style>
{CSS}
</style>
</head>
<body>
<div class="sheet">
{body_html}
</div>
</body>
</html>
"""


def find_edge() -> str | None:
    candidates = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None


def main() -> None:
    txt_files = sorted(DRAFTS_DIR.glob("draft_junbi_shomen_*.txt"))
    if not txt_files:
        print("ERROR: No draft TXT found. Run generate_first_brief.py first.")
        sys.exit(1)
    src = txt_files[-1]
    print(f"[input] {src}")

    txt = src.read_text(encoding="utf-8")
    html_out = txt_to_html(txt)

    html_path = src.with_suffix(".html")
    html_path.write_text(html_out, encoding="utf-8")
    print(f"[html ] {html_path}")

    edge = find_edge()
    pdf_path = src.with_suffix(".pdf")
    if edge:
        cmd = [
            edge,
            "--headless",
            "--disable-gpu",
            f"--print-to-pdf={pdf_path}",
            f"file:///{html_path.as_posix()}",
        ]
        print(f"[edge ] running headless...")
        subprocess.run(cmd, check=True, capture_output=True)
        # Edge sometimes returns before flushing the file; small wait.
        import time
        for _ in range(20):
            if pdf_path.exists() and pdf_path.stat().st_size > 0:
                break
            time.sleep(0.25)
        if pdf_path.exists():
            print(f"[pdf  ] {pdf_path}  ({pdf_path.stat().st_size:,} bytes)")
        else:
            print(f"[warn ] PDF was not generated at {pdf_path}")
            pdf_path = None
    else:
        print("[warn ] Microsoft Edge not found; skipping PDF.")
        pdf_path = None

    # Open both
    if sys.platform.startswith("win"):
        try:
            os.startfile(str(html_path))  # noqa
            print(f"[open ] HTML opened in default browser")
        except Exception as e:
            print(f"  open html failed: {e}")
        if pdf_path and pdf_path.exists():
            try:
                os.startfile(str(pdf_path))  # noqa
                print(f"[open ] PDF opened in default PDF viewer")
            except Exception as e:
                print(f"  open pdf failed: {e}")


if __name__ == "__main__":
    main()
