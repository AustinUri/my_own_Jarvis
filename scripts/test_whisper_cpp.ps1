param(
    [Parameter(Mandatory=$true)]
    [string]$WavPath,
    [ValidateSet('tiny','base','small','medium')]
    [string]$Model = 'small',
    [ValidateSet('auto','en','he')]
    [string]$Language = 'auto'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$WhisperRoot = Join-Path $ProjectRoot 'third_party\whisper.cpp'
$ExeCandidates = @(
    (Join-Path $WhisperRoot 'build\bin\Release\whisper-cli.exe'),
    (Join-Path $WhisperRoot 'whisper-cli.exe')
)
$Exe = $ExeCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $Exe) { throw 'whisper-cli.exe not found. Run setup_whisper_cpp_cpu.ps1 first.' }

$ModelCandidates = @(
    (Join-Path $WhisperRoot "models\ggml-$Model.bin"),
    (Join-Path $WhisperRoot "models\ggml-$Model.en.bin")
)
$ModelPath = $ModelCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $ModelPath) { throw "Model ggml-$Model(.en).bin not found in $WhisperRoot\models" }
if (-not (Test-Path $WavPath)) { throw "WAV file not found: $WavPath" }

$Args = @('-m', $ModelPath, '-f', $WavPath)
if ($Language -ne 'auto') {
    $Args += @('-l', $Language)
}
& $Exe @Args
