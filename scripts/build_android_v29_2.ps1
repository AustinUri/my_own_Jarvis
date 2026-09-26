$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$android = Join-Path $root 'android_companion'

# Keep machine-specific Android SDK paths out of the JARVIS package/repository.
$localProps = Join-Path $android 'local.properties'
if (-not (Test-Path $localProps)) {
    $sdk = $env:ANDROID_SDK_ROOT
    if (-not $sdk) { $sdk = $env:ANDROID_HOME }
    if (-not $sdk) { $sdk = Join-Path $env:LOCALAPPDATA 'Android\Sdk' }
    if (-not $sdk -or -not (Test-Path $sdk)) {
        throw "Android SDK not found. Install/open Android Studio once, or set ANDROID_SDK_ROOT."
    }
    $escaped = $sdk -replace '\\','\\\\' -replace ':','\:'
    Set-Content -Path $localProps -Value ("sdk.dir=" + $escaped) -Encoding ASCII
    Write-Host "[OK] Created local Android SDK mapping for this PC only." -ForegroundColor Green
}
Push-Location $android
try {
    Write-Host "Building JARVIS Companion v29.2 debug APK..." -ForegroundColor Cyan
    .\gradlew.bat assembleDebug
    $apk = Join-Path $android 'app\build\outputs\apk\debug\app-debug.apk'
    if (-not (Test-Path $apk)) { throw "Gradle completed but app-debug.apk was not found." }
    $out = Join-Path $root 'JARVIS_Companion_v29_2-debug.apk'
    Copy-Item $apk $out -Force
    Write-Host "[OK] Created $out" -ForegroundColor Green
} finally { Pop-Location }
