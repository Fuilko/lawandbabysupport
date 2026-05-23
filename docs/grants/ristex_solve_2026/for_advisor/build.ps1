# 日本語資料を DOCX/HTML/PDF に一括変換
# 使い方: PowerShell で本フォルダにて  .\build.ps1
# 必要ツール: pandoc, MiKTeX (lualatex)

$ErrorActionPreference = "Stop"
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

$inputs = @("01_letter_jp.md", "02_project_briefing_jp.md")
$out    = "RISTEX_鈴木先生ご相談資料_20260522"

Write-Host "[1/3] DOCX 生成中..." -ForegroundColor Cyan
pandoc @inputs -o "$out.docx" --toc --toc-depth=2 -V lang=ja

Write-Host "[2/3] HTML 生成中..." -ForegroundColor Cyan
pandoc @inputs -o "$out.html" --toc --toc-depth=2 -s --metadata title="RISTEX 鈴木先生ご相談資料" -V lang=ja

Write-Host "[3/3] PDF 生成中 (lualatex + ltjsarticle)..." -ForegroundColor Cyan
pandoc @inputs -o "$out.pdf" `
    --pdf-engine=lualatex `
    --toc --toc-depth=2 `
    -V lang=ja `
    -V documentclass=ltjsarticle `
    -V geometry:margin=2cm

Write-Host "`n完成:" -ForegroundColor Green
Get-ChildItem "$out.*" | Select-Object Name, Length, LastWriteTime | Format-Table
