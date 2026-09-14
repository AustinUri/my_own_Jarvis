$ErrorActionPreference = 'SilentlyContinue'
$taskName = 'JarvisV28AwayMode'
Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
Write-Host "JARVIS v29.1 Away Mode task removed." -ForegroundColor Cyan
