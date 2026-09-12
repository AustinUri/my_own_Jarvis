Write-Host "JARVIS v26 ships a zero-build runtime workspace in workspace_ui\dist." -ForegroundColor Cyan
Write-Host "The older React source tree is retained for reference, but rebuilding it would overwrite the v26 Control Center." -ForegroundColor Yellow
Write-Host "Do not run npm build for v26 unless you are intentionally porting the runtime workspace back into the React source tree."
