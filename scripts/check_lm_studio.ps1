$ErrorActionPreference = "Stop"
Write-Host "== LM Studio check ==" -ForegroundColor Cyan
try {
    $models = Invoke-RestMethod -UseBasicParsing -Uri "http://127.0.0.1:1234/v1/models" -TimeoutSec 5
    $models.data | Select-Object id, object | Format-Table
    if (@($models.data).Count -eq 0) {
        Write-Host "LM Studio server is running, but no model is loaded." -ForegroundColor Yellow
    }
} catch {
    Write-Host "LM Studio API is not reachable." -ForegroundColor Red
    Write-Host "Open LM Studio -> Developer -> Start Server, or run: lms server start"
    exit 1
}
