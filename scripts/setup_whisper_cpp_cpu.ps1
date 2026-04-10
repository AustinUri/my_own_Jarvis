param(
    [ValidateSet('tiny','base','small','medium')]
    [string]$Model = 'small',
    [switch]$ForceReclone
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Require-Command([string]$Name) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Missing required command: $Name. Install it first and rerun this script."
    }
}

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$ThirdPartyRoot = Join-Path $ProjectRoot 'third_party'
$SourceDir = Join-Path $ThirdPartyRoot 'whisper.cpp-src'
$AppWhisperDir = Join-Path $ThirdPartyRoot 'whisper.cpp'
$DestBinDir = Join-Path $AppWhisperDir 'build\bin\Release'
$DestModelDir = Join-Path $AppWhisperDir 'models'

Write-Host "== Jarvis whisper.cpp CPU setup ==" -ForegroundColor Cyan
Write-Host "Project root: $ProjectRoot"
Write-Host "Model: $Model"

Require-Command git
Require-Command cmake

New-Item -ItemType Directory -Force -Path $ThirdPartyRoot | Out-Null
New-Item -ItemType Directory -Force -Path $DestBinDir | Out-Null
New-Item -ItemType Directory -Force -Path $DestModelDir | Out-Null

if ($ForceReclone -and (Test-Path $SourceDir)) {
    Remove-Item -Recurse -Force $SourceDir
}

if (-not (Test-Path $SourceDir)) {
    Write-Host "Cloning whisper.cpp source..." -ForegroundColor Yellow
    git clone https://github.com/ggml-org/whisper.cpp.git $SourceDir
} else {
    Write-Host "Updating existing whisper.cpp source..." -ForegroundColor Yellow
    git -C $SourceDir pull --ff-only
}

Write-Host "Building whisper.cpp (Release, CPU)..." -ForegroundColor Yellow
cmake -S $SourceDir -B (Join-Path $SourceDir 'build') -DCMAKE_BUILD_TYPE=Release
cmake --build (Join-Path $SourceDir 'build') --config Release -j

$DownloadCmd = Join-Path $SourceDir 'models\download-ggml-model.cmd'
if (-not (Test-Path $DownloadCmd)) {
    throw "whisper.cpp model download script was not found: $DownloadCmd"
}

Write-Host "Downloading ggml model: $Model" -ForegroundColor Yellow
Push-Location $SourceDir
cmd /c "`"$DownloadCmd`" $Model"
Pop-Location

$BuiltExeCandidates = @(
    (Join-Path $SourceDir 'build\bin\Release\whisper-cli.exe'),
    (Join-Path $SourceDir 'build\bin\Release\main.exe'),
    (Join-Path $SourceDir 'build\bin\whisper-cli.exe'),
    (Join-Path $SourceDir 'build\bin\main.exe')
)
$BuiltExe = $BuiltExeCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $BuiltExe) {
    throw "Built whisper executable not found under $SourceDir\build\bin"
}

$ModelCandidates = @(
    (Join-Path $SourceDir "models\ggml-$Model.bin"),
    (Join-Path $SourceDir "models\ggml-$Model.en.bin")
)
$BuiltModel = $ModelCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $BuiltModel) {
    throw "Downloaded model not found in $SourceDir\models"
}

Copy-Item -Force $BuiltExe (Join-Path $DestBinDir 'whisper-cli.exe')
Copy-Item -Force $BuiltModel (Join-Path $DestModelDir (Split-Path $BuiltModel -Leaf))

Write-Host ""
Write-Host "Done." -ForegroundColor Green
Write-Host "Executable copied to: $DestBinDir\whisper-cli.exe"
Write-Host "Model copied to: $DestModelDir\$(Split-Path $BuiltModel -Leaf)"
Write-Host ""
Write-Host "In Jarvis settings:" -ForegroundColor Cyan
Write-Host "  - Set STT backend to whisper.cpp"
Write-Host "  - Set STT model to $Model"
Write-Host "  - Set language to Hebrew or English as needed"
