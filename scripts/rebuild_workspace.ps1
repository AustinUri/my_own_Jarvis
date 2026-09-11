$ErrorActionPreference = "Stop"
Set-Location (Join-Path (Split-Path -Parent $PSScriptRoot) "workspace_ui")
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    throw "npm is not installed. The included zero-build workspace in dist already works; Node is only needed to rebuild the React/TypeScript source."
}
Write-Host "Installing frontend development packages..." -ForegroundColor Cyan
npm install
Write-Host "Building React workspace..." -ForegroundColor Cyan
npm run build
Write-Host "Workspace rebuilt." -ForegroundColor Green
