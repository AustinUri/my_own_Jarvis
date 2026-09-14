$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$android = Join-Path $root 'android_companion'
Push-Location $android
try {
    Write-Host "Building JARVIS Companion v29.0 debug APK..." -ForegroundColor Cyan
    .\gradlew.bat assembleDebug
    $apk = Join-Path $android 'app\build\outputs\apk\debug\app-debug.apk'
    if (-not (Test-Path $apk)) { throw "Gradle completed but app-debug.apk was not found." }
    $out = Join-Path $root 'JARVIS_Companion_v29-debug.apk'
    Copy-Item $apk $out -Force
    Write-Host "[OK] Created $out" -ForegroundColor Green
} finally { Pop-Location }
