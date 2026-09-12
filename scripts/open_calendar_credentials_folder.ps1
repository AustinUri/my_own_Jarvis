$path = Join-Path $env:APPDATA "Jarvis\credentials"
New-Item -ItemType Directory -Force $path | Out-Null
Start-Process explorer.exe $path
Write-Host "Put your Google OAuth Desktop App JSON here and rename it to google_calendar_client.json"
