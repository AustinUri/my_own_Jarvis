Remove-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name "JarvisLocalAssistant" -ErrorAction SilentlyContinue
Write-Host "JARVIS start-with-Windows disabled."
