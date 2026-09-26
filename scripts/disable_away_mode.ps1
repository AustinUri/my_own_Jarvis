$ErrorActionPreference = 'SilentlyContinue'
$taskName = 'JarvisV28AwayMode'
Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
Write-Host "JARVIS v29.2 Away Mode task removed." -ForegroundColor Cyan
