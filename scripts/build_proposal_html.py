"""Build single self-contained HTML from markdown drafts."""
from pathlib import Path
import re
import html

ROOT = Path(r"D:\projects\LegalShield\docs\grants\ristex_solve_2026")
DRAFT = ROOT / "draft"
OUTREACH = ROOT / "outreach"
OUT = ROOT / "PROPOSAL_PACKAGE.html"

# Order of sections
SECTIONS = [
    ("summary", "エグゼクティブサマリー", None),
    ("draft_00", "全体ガイド", DRAFT / "00_README.md"),
    ("draft_01", "様式 1 基本事項", DRAFT / "01_basic.md"),
    ("draft_02", "様式 2 構想", DRAFT / "02_concept.md"),
    ("draft_03", "様式 3 独創性・優位性", DRAFT / "03_originality.md"),
    ("draft_04", "様式 4 目標・実施計画", DRAFT / "04_plan.md"),
    ("draft_05", "様式 4-2 予算計画", DRAFT / "05_budget.md"),
    ("draft_06", "様式 5 実施体制", DRAFT / "06_team.md"),
    ("draft_07", "様式 6 実績", DRAFT / "07_achievements.md"),
    ("draft_08", "様式 7-8 その他", DRAFT / "08_others.md"),
    ("draft_09", "16 評価視点セルフチェック", DRAFT / "09_review_checklist.md"),
    ("out_00", "外聯戦略", OUTREACH / "00_strategy.md"),
    ("out_01", "汎用紹介書（PDF 化用）", OUTREACH / "01_project_intro_jp.md"),
    ("out_02", "Cover ① 鈴木先生", OUTREACH / "02_cover_suzuki.md"),
    ("out_03", "Cover ② 高知ローカル", OUTREACH / "03_cover_kochi_local.md"),
    ("out_04", "Cover ③ 東京 NPO・弁連", OUTREACH / "04_cover_tokyo_npo.md"),
    ("out_05", "Cover ④⑤ POSSE / Civic Tech", OUTREACH / "05_cover_posse_civic_tech.md"),
    ("out_06", "13 日スプリント計画", OUTREACH / "06_sprint_13days.md"),
    ("grant_landscape", "助成金カレンダー（並行応募戦略）", ROOT / "GRANT_LANDSCAPE.md"),
]


def md_to_html(md: str) -> str:
    """Minimal markdown -> HTML converter (handles our drafts)."""
    lines = md.split("\n")
    out = []
    in_code = False
    in_table = False
    in_list = False
    list_type = None
    table_rows = []

    def flush_table():
        nonlocal table_rows, in_table
        if not table_rows:
            return
        out.append("<table>")
        # header
        head = table_rows[0]
        out.append("<tr>" + "".join(f"<th>{c}</th>" for c in head) + "</tr>")
        # skip separator row (index 1)
        for row in table_rows[2:]:
            out.append("<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>")
        out.append("</table>")
        table_rows = []
        in_table = False

    def flush_list():
        nonlocal in_list, list_type
        if in_list:
            out.append(f"</{list_type}>")
            in_list = False
            list_type = None

    def inline(s: str) -> str:
        # escape first then re-enable formatting
        s = html.escape(s)
        s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
        s = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", s)
        s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
        s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', s)
        return s

    for raw in lines:
        line = raw.rstrip()

        # code fence
        if line.startswith("```"):
            flush_list()
            flush_table()
            if in_code:
                out.append("</pre>")
                in_code = False
            else:
                out.append("<pre>")
                in_code = True
            continue
        if in_code:
            out.append(html.escape(raw))
            continue

        # table
        if "|" in line and line.strip().startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            cells_html = [inline(c) for c in cells]
            if not in_table:
                flush_list()
                in_table = True
            table_rows.append(cells_html)
            continue
        else:
            if in_table:
                flush_table()

        # blank
        if not line.strip():
            flush_list()
            out.append("")
            continue

        # headings
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            flush_list()
            level = len(m.group(1))
            text = inline(m.group(2))
            out.append(f"<h{level+1}>{text}</h{level+1}>")  # shift down (h1 reserved)
            continue

        # blockquote
        if line.startswith(">"):
            flush_list()
            out.append(f"<blockquote>{inline(line.lstrip('> '))}</blockquote>")
            continue

        # list
        if re.match(r"^\s*[-*+]\s+", line):
            if not in_list or list_type != "ul":
                flush_list()
                out.append("<ul>")
                in_list = True
                list_type = "ul"
            text = re.sub(r"^\s*[-*+]\s+", "", line)
            out.append(f"<li>{inline(text)}</li>")
            continue
        if re.match(r"^\s*\d+\.\s+", line):
            if not in_list or list_type != "ol":
                flush_list()
                out.append("<ol>")
                in_list = True
                list_type = "ol"
            text = re.sub(r"^\s*\d+\.\s+", "", line)
            out.append(f"<li>{inline(text)}</li>")
            continue

        # plain paragraph
        flush_list()
        out.append(f"<p>{inline(line)}</p>")

    flush_table()
    flush_list()
    if in_code:
        out.append("</pre>")
    return "\n".join(out)


def main():
    head = """<!DOCTYPE html>
<html lang="ja"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>RISTEX SOLVE 2026 提案パッケージ — LegalShield / FEWN</title>
<style>
:root{--bg:#fafaf8;--fg:#1a1a1a;--muted:#666;--accent:#b8002b;--accent2:#0a4d6f;
--warn:#c46500;--ok:#1a7a3a;--line:#e3e0db;--code:#f4f0ea;--sw:280px;}
*{box-sizing:border-box}
html,body{margin:0;padding:0;background:var(--bg);color:var(--fg);
 font-family:"Hiragino Kaku Gothic ProN","Yu Gothic","Meiryo","Noto Sans CJK JP",sans-serif;
 line-height:1.75;font-size:15px;}
a{color:var(--accent2);text-decoration:none}a:hover{text-decoration:underline}
code{background:var(--code);padding:1px 5px;border-radius:3px;font-size:0.9em;
 font-family:"Consolas","Menlo",monospace}
pre{background:var(--code);padding:14px;border-radius:6px;overflow-x:auto;font-size:0.82em;
 line-height:1.5;border-left:3px solid var(--accent2);
 font-family:"Consolas","Menlo",monospace;white-space:pre}
#sidebar{position:fixed;top:0;left:0;width:var(--sw);height:100vh;overflow-y:auto;
 background:#fff;border-right:1px solid var(--line);padding:24px 18px;font-size:13px}
#sidebar h2{font-size:14px;margin:0 0 12px;color:var(--accent);letter-spacing:0.05em}
#sidebar ol{list-style:none;padding:0;margin:0}
#sidebar li{margin:4px 0;line-height:1.45}
#sidebar a{display:block;padding:3px 6px;border-radius:3px;color:var(--fg)}
#sidebar a:hover{background:#f0ebe3;text-decoration:none}
#sidebar .ttl{font-weight:700;font-size:15px;color:var(--accent);display:block;
 margin-bottom:6px;line-height:1.3}
#sidebar .sub{font-size:11px;color:var(--muted);margin-bottom:18px}
main{margin-left:var(--sw);padding:40px 50px;max-width:980px}
h1{font-size:30px;line-height:1.3;margin:0 0 8px;color:var(--accent);
 border-bottom:3px solid var(--accent);padding-bottom:12px}
h1 .sub{display:block;font-size:17px;color:var(--muted);font-weight:400;margin-top:6px}
h2{font-size:23px;margin:44px 0 14px;color:var(--accent2);
 border-left:5px solid var(--accent2);padding-left:14px}
h3{font-size:18px;margin:24px 0 10px;color:var(--accent)}
h4{font-size:15.5px;margin:18px 0 8px;color:var(--accent2)}
h5{font-size:14px;margin:14px 0 6px;color:#333;font-weight:600}
p{margin:6px 0 12px}
blockquote{border-left:4px solid var(--accent);background:#fff5f0;margin:12px 0;
 padding:10px 16px;color:#333;border-radius:0 4px 4px 0}
table{border-collapse:collapse;width:100%;margin:12px 0;font-size:0.92em;background:#fff;
 border-radius:4px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.04)}
th{background:var(--accent2);color:#fff;padding:7px 9px;text-align:left;font-weight:600}
td{padding:6px 9px;border-bottom:1px solid var(--line);vertical-align:top}
tr:nth-child(even) td{background:#faf8f4}
.hero{background:linear-gradient(135deg,#fff,#fff5f0);padding:28px;border-radius:8px;
 margin:24px 0;border:1px solid var(--line);box-shadow:0 2px 8px rgba(0,0,0,0.04)}
.three-facts{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin:20px 0}
.three-facts .f{background:#fff;padding:18px;border-radius:6px;border-top:4px solid var(--accent);
 box-shadow:0 1px 3px rgba(0,0,0,0.06)}
.three-facts .f .big{font-size:30px;font-weight:700;color:var(--accent);line-height:1.1;margin:6px 0}
.three-facts .f .lbl{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:0.06em}
.three-facts .f .desc{font-size:12.5px;color:#333;margin-top:6px}
.callout{padding:12px 16px;border-radius:6px;margin:14px 0}
.c-warn{background:#fff5e6;border-left:4px solid var(--warn)}
.c-ok{background:#ebf7ef;border-left:4px solid var(--ok)}
.c-red{background:#fde9ec;border-left:4px solid var(--accent)}
.c-blue{background:#e9f3f8;border-left:4px solid var(--accent2)}
.badge{display:inline-block;padding:2px 8px;border-radius:99px;font-size:11px;
 font-weight:600;margin:0 3px 3px 0}
.b-red{background:#fde2e2;color:var(--accent)}
.b-blue{background:#dceaf0;color:var(--accent2)}
.b-green{background:#dceadc;color:var(--ok)}
.b-orange{background:#fbe6cd;color:var(--warn)}
details{margin:14px 0;background:#fff;border:1px solid var(--line);border-radius:5px;padding:14px 18px}
details[open]{box-shadow:0 2px 6px rgba(0,0,0,0.05)}
summary{cursor:pointer;font-weight:700;color:var(--accent2);outline:none;user-select:none;font-size:15px}
summary:hover{color:var(--accent)}
.print-btn{position:fixed;top:14px;right:20px;background:var(--accent);color:#fff;
 padding:9px 16px;border-radius:99px;border:none;cursor:pointer;font-size:12.5px;
 font-weight:600;box-shadow:0 4px 12px rgba(184,0,43,0.3);z-index:100}
.print-btn:hover{background:#8e0021}
ul,ol{padding-left:24px;margin:6px 0}ul li,ol li{margin:3px 0}
footer{margin-top:60px;padding:20px 0;border-top:1px solid var(--line);
 color:var(--muted);font-size:13px;text-align:center}
@media print{
 #sidebar,.print-btn{display:none}main{margin-left:0;padding:20px;max-width:none}
 body{font-size:10.5pt}h1,h2,h3{page-break-after:avoid}
 table,blockquote,.callout{page-break-inside:avoid}
 details{page-break-inside:avoid}details summary~*{display:block !important}
 details:not([open])>summary~*{display:block !important}
}
@media (max-width:900px){:root{--sw:0}#sidebar{display:none}
 main{margin-left:0;padding:20px 16px}.three-facts{grid-template-columns:1fr}}
</style></head><body>
<button class="print-btn" onclick="window.print()">印刷 / PDF 保存</button>
<nav id="sidebar">
<span class="ttl">RISTEX SOLVE 2026<br>提案パッケージ</span>
<span class="sub">LegalShield / FEWN<br>2026.5.21 / 締切まで 13 日</span>
<h2>目次</h2><ol>
__TOC__
</ol></nav>
<main>
"""

    toc_parts = []
    body_parts = []

    # Hero / summary block (hard-coded)
    body_parts.append("""
<section id="summary">
<h1>JST RISTEX SOLVE for SDGs 2026
<span class="sub">暗数の彼方の被害者をつなぐ — 連続加害者の暗号学的検知ネットワーク（FEWN）による「誰一人置き去りにしない」安全社会の共創</span>
</h1>
<div class="hero">
<p style="font-size:15.5px;margin:0">
<strong>キーアイデア</strong>：被害者が顔写真や位置情報を一切サーバに送らずに「同じ加害者を記録した別の被害者」を <em>暗号学的にのみ</em> 検知する分散ネットワーク。米国 Callisto（10 年実証）に <strong>顔エンベディング LSH を加えて改名による逃亡を貫通</strong>する世界初の社会実装。
</p>
</div>
<h2>採択評価サマリー</h2>
<table>
<tr><th>項目</th><th>値</th></tr>
<tr><td>公募</td><td>JST RISTEX SDGs ソリューション創出フェーズ（2026 年度）</td></tr>
<tr><td>締切</td><td><strong>2026 年 6 月 3 日（水）正午</strong> e-Rad</td></tr>
<tr><td>期間</td><td>2026.10 〜 2030.3（3 年 6 ヶ月）</td></tr>
<tr><td>予算</td><td>直接経費 約 5,450 万円（上限 1,900 万円/年）</td></tr>
<tr><td>採択枠</td><td>2 件程度（採択率 <strong>5-10%</strong>）</td></tr>
<tr><td>対象 SDGs</td><td><span class="badge b-red">Goal 5</span> <span class="badge b-blue">Goal 16</span> <span class="badge b-green">Goal 10</span></td></tr>
<tr><td>実施地域</td><td>東京・大阪・<strong>高知</strong>＋台湾連携（加点）</td></tr>
<tr><td>研究代表者</td><td>確定待ち（鈴木保志教授 等大学側パートナー）</td></tr>
<tr><td>協働実施者</td><td>あなた（光伊Forest 等法人代表）</td></tr>
</table>

<div class="callout c-warn">
<strong>採択確率について</strong>：本年度は 5-10%。それでも応募する価値は十分。<strong>応募準備プロセス自体がステークホルダー対話・現場知蓄積・連携体制構築になる</strong>ため、不採択でも来年度応募の地盤として有効。
</div>

<h2>直視すべき三つの定量的事実</h2>
<p>本提案の出発点。これを掛け合わせると、日本社会の制度設計上の真空地帯が浮かび上がる。</p>
<div class="three-facts">
<div class="f"><div class="lbl">沈黙率</div><div class="big">60-70%</div>
<div class="desc">性暴力被害者の女性 6 割・男性 7 割が <strong>誰にも相談しない</strong>。<br><span style="color:var(--muted);font-size:11px">内閣府 男女間における暴力に関する調査 R5</span></div></div>
<div class="f"><div class="lbl">ギャップ係数</div><div class="big">18.36×</div>
<div class="desc">ストーカー相談 19,843 件に対し検挙 1,081 件。<br><span style="color:var(--muted);font-size:11px">警察庁 令和 5 年版</span></div></div>
<div class="f"><div class="lbl">連続加害集中</div><div class="big">4% / 5.8件</div>
<div class="desc">男性人口の 4% の連続加害者が <strong>平均 5.8 件の被害</strong>を生む。<br><span style="color:var(--muted);font-size:11px">Lisak &amp; Miller 2002</span></div></div>
</div>
<div class="callout c-red">
<strong>制度設計上の真空地帯</strong>：日本社会には「同じ加害者の別の被害者と出会う仕組み」がどこにも存在しない。被害者は単独で警察を訪れて「証拠不十分」として帰され、4% の連続加害者は事実上の野放しになる。<strong>本プロジェクトはこの真空を、暗号学的に塞ぐ。</strong>
</div>

<h2>応募資格の現実 — あなたは資格充分</h2>
<div class="callout c-ok">
<strong>教授必須ではありません。</strong> 公募要領が要求するのは <strong>「研究代表者 OR 協働実施者の片方が大学等所属」</strong> のみ。あなた自身は <strong>協働実施者</strong>（光伊Forest 代表）として応募可能。鈴木先生に研究代表者をお願いする形が最も自然。
</div>

<h2>5 つの強み（採択ポイント）</h2>
<table>
<tr><th>強み</th><th>RISTEX 公募要領との整合</th></tr>
<tr><td><strong>① SDGs Goal 5 主軸</strong></td><td>2025 SDR で日本のジェンダー平等達成度が最低水準。プログラム総括が「特に積極的な提案を期待」と明示（p.10）</td></tr>
<tr><td><strong>② 技術シーズ既存</strong></td><td>FaceNet・LSH・PSI・Threshold Crypto・Callisto は全て査読論文＋商用実装あり。「研究室レベル可能性試験は終了」要件を厳密充足</td></tr>
<tr><td><strong>③ 「誰一人置き去りにしない」直撃</strong></td><td>沈黙率 60% という「置き去り」の数字を中核に据える</td></tr>
<tr><td><strong>④ 複数地域＋海外連携</strong></td><td>東京・大阪・高知の 3 地域＋台湾国際連携で加点</td></tr>
<tr><td><strong>⑤ 既に構築済みの基盤</strong></td><td>JUDB／EVIDENCE_BASE／FEWN 設計書／35 件文献／クローラ群が完成</td></tr>
</table>

<h2>4 つのリスクと対応</h2>
<table>
<tr><th>リスク</th><th>対応</th></tr>
<tr><td>研究代表者の専門性（森林工学）</td><td>主たる実施者に情報法／犯罪学研究者を配置、外部倫理委員 3 名で補強</td></tr>
<tr><td>13 日間の準備期間</td><td>IRB・警察協定は「採択後の確実な締結見込み」として記述</td></tr>
<tr><td>修士＋独立開発者</td><td>協働実施者として位置付け、マネジメント経験ある研究代表者を配置</td></tr>
<tr><td>倫理的機微性</td><td>外部倫理委員 + 弁連監査 + 大学 IRB の三重保護</td></tr>
</table>
</section>
""")

    toc_parts.append('<li><a href="#summary"><strong>エグゼクティブサマリー</strong></a></li>')
    toc_parts.append('<li style="margin-top:12px;color:var(--muted);font-size:11px">━━ 提案書本文 ━━</li>')

    # Convert each markdown file
    for sec_id, label, path in SECTIONS:
        if sec_id == "summary":
            continue
        if path is None or not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        body_html = md_to_html(text)
        body_parts.append(f'<section id="{sec_id}"><details><summary>📋 {label}</summary>{body_html}</details></section>')
        toc_parts.append(f'<li><a href="#{sec_id}">{label}</a></li>')
        if sec_id == "draft_09":
            toc_parts.append('<li style="margin-top:12px;color:var(--muted);font-size:11px">━━ 外聯・実行 ━━</li>')

    footer = """
<footer>
<p>RISTEX SOLVE 2026 提案パッケージ v1 / 生成: 2026-05-21<br>
LegalShield / FEWN — 暗号学的協調による「誰一人置き去りにしない」安全社会の共創<br>
本書は内部用ドラフト。提出版は Word 様式 form_solution_solve2026.docx に貼り込み・PDF 化のこと</p>
</footer>
</main></body></html>"""

    html_text = head.replace("__TOC__", "\n".join(toc_parts)) + "\n".join(body_parts) + footer
    OUT.write_text(html_text, encoding="utf-8")
    print(f"Generated: {OUT} ({OUT.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
