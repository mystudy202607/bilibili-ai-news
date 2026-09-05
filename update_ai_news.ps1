# Bilibili AI news daily auto-update script
$ErrorActionPreference = "Stop"

$dir = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = "C:\Users\Administrator\AppData\Local\Programs\Python\Python311\python.exe"
$log = Join-Path $dir "bilibili_ai_news_update.log"
$stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

try {
    "[$stamp] daily update started" | Out-File -FilePath $log -Append -Encoding utf8

    & $python -X utf8 (Join-Path $dir "bilibili_ai_news_collector.py") 2>&1 |
        Out-String | Out-File -FilePath $log -Append -Encoding utf8

    & $python -X utf8 (Join-Path $dir "build_ai_news_page.py") 2>&1 |
        Out-String | Out-File -FilePath $log -Append -Encoding utf8

    "[$stamp] daily update finished" | Out-File -FilePath $log -Append -Encoding utf8
}
catch {
    "[$stamp] daily update failed: $_" | Out-File -FilePath $log -Append -Encoding utf8
    exit 1
}
