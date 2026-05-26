# Build briefing markdown -> styled HTML -> PDF using Edge headless
# Usage:  .\build.ps1
$ErrorActionPreference = "Stop"

$InputMd = "01_meeting_brief_toyota_20260525.md"
$OutBase = "LegalShield_トヨタ財団ご相談資料_20260525"
$BrowserCandidates = @(
    "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    "C:\Program Files\Google\Chrome\Application\chrome.exe"
)
$Browser = $BrowserCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $Browser) { throw "Edge / Chrome not found." }
Write-Host "Using browser: $Browser" -ForegroundColor Cyan

# 1. Markdown -> HTML
$mdPath = Join-Path $PSScriptRoot $InputMd
$htmlPath = Join-Path $PSScriptRoot "$OutBase.html"
$pdfPath = Join-Path $PSScriptRoot "$OutBase.pdf"

Write-Host "[1/2] Markdown -> HTML ..." -ForegroundColor Cyan
$py = @"
import sys, markdown, html as htmllib, pathlib, re
md_text = pathlib.Path(r'$mdPath').read_text(encoding='utf-8')
# Strip front matter (YAML)
md_text = re.sub(r'^---\n.*?\n---\n', '', md_text, count=1, flags=re.S)
body = markdown.markdown(md_text, extensions=['tables','fenced_code','toc'])
css = '''
@page { size: A4; margin: 18mm 14mm 18mm 14mm; }
* { box-sizing: border-box; }
body { font-family: 'Yu Gothic UI', '游ゴシック', 'Meiryo', 'Hiragino Sans', sans-serif;
       color: #1a1a1a; line-height: 1.65; font-size: 10.5pt; max-width: 100%; margin: 0; padding: 0 }
h1 { font-size: 18pt; color: #0a3a73; border-bottom: 3px solid #0a3a73; padding-bottom: 6px; margin-top: 22pt }
h2 { font-size: 14pt; color: #0a3a73; border-left: 5px solid #0a3a73; padding-left: 10px; margin-top: 20pt }
h3 { font-size: 12pt; color: #2a4a73; margin-top: 14pt }
h4 { font-size: 11pt; color: #2a4a73 }
p, li { font-size: 10.5pt; text-align: justify }
table { border-collapse: collapse; width: 100%; margin: 8pt 0; page-break-inside: avoid; font-size: 9.5pt }
th, td { border: 1px solid #aab2c0; padding: 5pt 7pt; vertical-align: top }
th { background: #e8eef7; color: #0a3a73; font-weight: 600 }
code, pre { font-family: 'Cascadia Mono', Consolas, monospace; font-size: 9.5pt; background: #f4f6fa; padding: 2px 4px; border-radius: 3px }
pre { padding: 8pt 10pt; overflow-x: auto; page-break-inside: avoid }
blockquote { border-left: 4px solid #0a3a73; background: #f4f6fa; padding: 6pt 12pt; margin: 8pt 0; color: #2a4a73 }
hr { border: 0; border-top: 1px dashed #aab2c0; margin: 14pt 0 }
ul, ol { padding-left: 22pt }
li > p { margin: 2pt 0 }
strong { color: #0a3a73 }
'''
out = f'''<!doctype html><html lang="ja"><head><meta charset="utf-8">
<title>LegalShield トヨタ財団ご相談資料</title>
<style>{css}</style></head><body>{body}</body></html>'''
pathlib.Path(r'$htmlPath').write_text(out, encoding='utf-8')
print('HTML OK:', r'$htmlPath')
"@
python -c $py
if ($LASTEXITCODE -ne 0) { throw "Python markdown step failed" }

Write-Host "[2/2] HTML -> PDF (headless Edge/Chrome) ..." -ForegroundColor Cyan
$fileUrl = "file:///" + ($htmlPath -replace '\\','/' -replace ' ','%20')
& $Browser --headless=new --disable-gpu --no-pdf-header-footer "--print-to-pdf=$pdfPath" $fileUrl | Out-Null
Start-Sleep -Seconds 2
if (-not (Test-Path $pdfPath)) { throw "PDF was not generated" }

Write-Host "`n完成:" -ForegroundColor Green
Get-Item $htmlPath, $pdfPath | Select-Object Name, @{N='Size(KB)';E={[math]::Round($_.Length/1KB,1)}}, LastWriteTime | Format-Table
Write-Host "PDF: $pdfPath" -ForegroundColor Yellow
