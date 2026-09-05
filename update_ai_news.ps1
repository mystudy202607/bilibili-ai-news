# Bilibili AI news daily auto-update + auto git push
$ErrorActionPreference = "Stop"

$dir = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = "C:\Users\Administrator\AppData\Local\Programs\Python\Python311\python.exe"
$repo = Join-Path $dir "bilibili-ai-news"
$log = Join-Path $dir "bilibili_ai_news_update.log"
$stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

try {
    "[$stamp] daily update started" | Out-File -FilePath $log -Append -Encoding utf8

    & $python -X utf8 (Join-Path $dir "bilibili_ai_news_collector.py") 2>&1 |
        Out-String | Out-File -FilePath $log -Append -Encoding utf8

    & $python -X utf8 (Join-Path $dir "build_ai_news_page.py") 2>&1 |
        Out-String | Out-File -FilePath $log -Append -Encoding utf8

    # copy fresh snapshot into the github repo folder
    Copy-Item -LiteralPath (Join-Path $dir "bilibili_ai_news\index.html") -Destination (Join-Path $repo "index.html") -Force
    Copy-Item -LiteralPath (Join-Path $dir "bilibili_ai_news.json") -Destination (Join-Path $repo "bilibili_ai_news.json") -Force
    Copy-Item -LiteralPath (Join-Path $dir "bilibili_ai_news_history.json") -Destination (Join-Path $repo "bilibili_ai_news_history.json") -Force

    # auto git commit + push
    Push-Location $repo
    git add -A 2>&1 | Out-String | Out-File -FilePath $log -Append -Encoding utf8
    $commit = git commit -m "daily snapshot $stamp" 2>&1 | Out-String
    $commit | Out-File -FilePath $log -Append -Encoding utf8
    if ($LASTEXITCODE -eq 0) {
        git push 2>&1 | Out-String | Out-File -FilePath $log -Append -Encoding utf8
        "[$stamp] pushed to github" | Out-File -FilePath $log -Append -Encoding utf8
    } else {
        "[$stamp] no changes to push" | Out-File -FilePath $log -Append -Encoding utf8
    }
    Pop-Location

    "[$stamp] daily update finished" | Out-File -FilePath $log -Append -Encoding utf8
}
catch {
    "[$stamp] daily update failed: $_" | Out-File -FilePath $log -Append -Encoding utf8
    exit 1
}
