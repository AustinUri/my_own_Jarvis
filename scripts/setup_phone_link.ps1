$ErrorActionPreference = 'Stop'
Write-Host "JARVIS v26 secure phone link setup" -ForegroundColor Cyan

$tailscale = Get-Command tailscale -ErrorAction SilentlyContinue
if (-not $tailscale) {
    Write-Host "Tailscale CLI was not found." -ForegroundColor Yellow
    Write-Host "Install the official Tailscale app on this PC and your Android phone, sign both into the same private tailnet, then run this script again."
    exit 1
}

Write-Host "Checking Tailscale..."
& tailscale status | Out-Host

Write-Host "`nConfiguring PRIVATE tailnet-only HTTPS access to JARVIS phone bridge (localhost:8766)..." -ForegroundColor Cyan
Write-Host "This script does NOT run 'tailscale funnel' and does not intentionally expose JARVIS to the public internet." -ForegroundColor DarkGray
& tailscale serve --bg localhost:8766

Write-Host "`nServe status:" -ForegroundColor Cyan
& tailscale serve status | Out-Host
Write-Host "`nNow open JARVIS > Phone Link > Create pairing code." -ForegroundColor Green
