$ErrorActionPreference = 'Stop'
Write-Host "JARVIS v29.1 secure phone link setup" -ForegroundColor Cyan

$tsExe = (Get-Command tailscale -ErrorAction SilentlyContinue).Source
if (-not $tsExe) {
    $candidate = "C:\Program Files\Tailscale\tailscale.exe"
    if (Test-Path $candidate) { $tsExe = $candidate }
}
if (-not $tsExe) {
    Write-Host "Tailscale CLI was not found in PATH or C:\Program Files\Tailscale." -ForegroundColor Yellow
    Write-Host "Install/sign in to Tailscale on this PC and your Android phone, then run this script again."
    exit 1
}

Write-Host "Checking Tailscale..."
& $tsExe status | Out-Host

$statusJson = & $tsExe status --json | ConvertFrom-Json
$dns = [string]$statusJson.Self.DNSName
$dns = $dns.TrimEnd('.')
$ip = @($statusJson.Self.TailscaleIPs | Where-Object { $_ -like '100.*' })[0]

Write-Host "`nConfiguring PRIVATE tailnet-only HTTPS access to JARVIS phone bridge (port 8766)..." -ForegroundColor Cyan
Write-Host "This script never enables Tailscale Funnel/public exposure." -ForegroundColor DarkGray
& $tsExe serve --bg 8766

Write-Host "`nServe status:" -ForegroundColor Cyan
& $tsExe serve status | Out-Host
Write-Host "`nV28 COMPANION VALUES" -ForegroundColor Green
Write-Host "Secure server URL : https://$dns"
Write-Host "DNS fallback IP   : $ip"
Write-Host ""
Write-Host "IMPORTANT: Keep the HTTPS .ts.net URL in the phone app." -ForegroundColor Yellow
Write-Host "If MagicDNS is slow/unreachable on Android, enter the fallback IP in the new V28 fallback field."
Write-Host "The app connects to that private IP while still validating HTTPS against the .ts.net hostname."
Write-Host "`nNow open JARVIS > Mobile > Phone Link > Test PC link, then Create pairing code." -ForegroundColor Green
