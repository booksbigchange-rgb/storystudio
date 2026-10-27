<# Starts the newest installed unified portable build (or -Version), or runs its self-test. #>
param(
    [string]$Version,
    [switch]$SelfTest,
    [string]$StudioRoot
)
$ErrorActionPreference = 'Stop'
if (-not $StudioRoot) {
    . (Join-Path $PSScriptRoot 'environment.ps1')
    $StudioRoot = $env:STORY_STUDIO
}
$exports = Join-Path $StudioRoot 'exports'
if ($Version) {
    $folder = Join-Path $exports ('unified-portable-' + $Version)
} else {
    $found = Get-ChildItem -LiteralPath $exports -Directory -Filter 'unified-portable-*' -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -notmatch 'validation' -and (Test-Path -LiteralPath (Join-Path $_.FullName 'StoryStudio.exe')) } |
        Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if (-not $found) { throw 'No unified portable build is installed. Run Install-StoryStudio-Unified-Portable.cmd with the downloaded zip first.' }
    $folder = $found.FullName
}
$app = Join-Path $folder 'StoryStudio.exe'
if (-not (Test-Path -LiteralPath $app)) { throw "StoryStudio.exe not found in $folder" }
if ($SelfTest) {
    $output = Join-Path $exports ('unified-portable-validation-' + (Split-Path $folder -Leaf).Substring(17) + '-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
    $process = Start-Process -FilePath $app -ArgumentList @('--self-test', '--output', ('"' + $output + '"')) -WorkingDirectory $folder -WindowStyle Hidden -PassThru
    if (-not $process.WaitForExit(600000)) { $process.Kill(); throw 'Self-test timed out after 10 minutes' }
    if ($process.ExitCode -ne 0) { Get-Content -LiteralPath (Join-Path $output 'selftest.log') -ErrorAction SilentlyContinue; throw "Self-test failed: $($process.ExitCode)" }
    Write-Output "PASS: self-test results in $output"
} else {
    Start-Process -FilePath $app -WorkingDirectory $folder
}
