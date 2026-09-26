$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)
$root = (Get-Location).Path
$pythonw = Join-Path $root '.venv\Scripts\pythonw.exe'
$main = Join-Path $root 'main.py'
if (-not (Test-Path $pythonw)) { throw "Missing .venv. Run .\scripts\setup_windows.ps1 first." }

$taskName = 'JarvisV28AwayMode'
$action = New-ScheduledTaskAction -Execute $pythonw -Argument ('"' + $main + '" --background') -WorkingDirectory $root
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RestartCount 8 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit (New-TimeSpan -Days 3650)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
$task = New-ScheduledTask -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description 'JARVIS v29.2 Away Mode: starts the headless core at logon and restarts it after unexpected exits.'
Register-ScheduledTask -TaskName $taskName -InputObject $task -Force | Out-Null
Write-Host "[OK] JARVIS v29.2 Away Mode enabled." -ForegroundColor Green
Write-Host "Task: $taskName"
Write-Host "It starts the JARVIS core at your Windows logon and restarts the process after unexpected exits."
Write-Host "For recovery after a full power outage, the PC still needs BIOS power-restore and a Windows sign-in strategy appropriate for your security needs."
