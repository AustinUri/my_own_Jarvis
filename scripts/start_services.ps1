$ErrorActionPreference = "Continue"
Write-Host "== Starting JARVIS local services ==" -ForegroundColor Cyan
if (Get-Command lms -ErrorAction SilentlyContinue) { lms server start } else { Write-Host "[WARN] lms command not found." -ForegroundColor Yellow }
if (Get-Command docker -ErrorAction SilentlyContinue) {
    $exists = docker ps -a --filter "name=^/searxng$" --format "{{.Names}}" 2>$null
    if ($exists -eq "searxng") { docker start searxng | Out-Null; Write-Host "SearXNG started." }
    else { Write-Host "[WARN] No Docker container named 'searxng' exists." -ForegroundColor Yellow }
} else { Write-Host "[WARN] Docker command not found." -ForegroundColor Yellow }
