# Register a Windows scheduled task: run daily at 08:00
$ErrorActionPreference = "Stop"

$taskName = "BilibiliAINewsDailyUpdate"
$updateScript = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "update_ai_news.ps1"

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument (
    "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$updateScript`""
)
$trigger = New-ScheduledTaskTrigger -Daily -At "08:00"
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 1)

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings `
    -Description "Daily Bilibili AI news auto update" -Force

$info = Get-ScheduledTaskInfo -TaskName $taskName
Get-ScheduledTask -TaskName $taskName |
    Select-Object TaskName, State, @{N="NextRun";E={$info.NextRunTime}}
