$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$android = Join-Path $root 'android_companion'
if (-not (Test-Path $android)) { throw "android_companion folder not found: $android" }

Write-Host "Building JARVIS Companion v28.2 debug APK..." -ForegroundColor Cyan
Push-Location $android
try {
    & .\gradlew.bat clean assembleDebug
    if ($LASTEXITCODE -ne 0) { throw "Gradle build failed with exit code $LASTEXITCODE" }
    $apk = Join-Path $android 'app\build\outputs\apk\debug\app-debug.apk'
    if (-not (Test-Path $apk)) { throw "Gradle completed but APK was not found: $apk" }
    $out = Join-Path $root 'JARVIS_Companion_v28_2-debug.apk'
    Copy-Item $apk $out -Force
    Write-Host "`nSUCCESS" -ForegroundColor Green
    Write-Host "APK: $out"
    Write-Host "Install this APK on the Samsung after uninstalling/replacing the previous development build if Android requests it."
} finally {
    Pop-Location
}
