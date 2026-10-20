<#
Installs a downloaded StoryStudio Unified portable zip into a NEW versioned folder:
  <studio>\exports\unified-portable-<version>
Never overwrites or modifies an existing folder (including the earlier exports\portable-766646f build).
The zip's SHA-256 is checked first, then every extracted file against SHA256SUMS.txt before the folder appears.
#>
param(
    [Parameter(Mandatory = $true)][string]$Zip,
    [string]$Sha256,
    [string]$StudioRoot
)
$ErrorActionPreference = 'Stop'
if (-not $StudioRoot) {
    . (Join-Path $PSScriptRoot 'environment.ps1')
    $StudioRoot = $env:STORY_STUDIO
}
$StudioRoot = (Resolve-Path -LiteralPath $StudioRoot).Path
$zipFile = (Resolve-Path -LiteralPath $Zip).Path
if (-not $Sha256) {
    $sidecar = $zipFile + '.sha256'
    if (-not (Test-Path -LiteralPath $sidecar)) { throw "Give -Sha256 or keep '$([IO.Path]::GetFileName($sidecar))' beside the zip." }
    $Sha256 = [regex]::Match((Get-Content -LiteralPath $sidecar -Raw), '[A-Fa-f0-9]{64}').Value
}
$actual = (Get-FileHash -LiteralPath $zipFile -Algorithm SHA256).Hash
if ($actual -ne $Sha256.ToUpper()) { throw "Zip checksum mismatch. Expected $Sha256, got $actual. Nothing was installed." }

Add-Type -AssemblyName System.IO.Compression.FileSystem
$archive = [IO.Compression.ZipFile]::OpenRead($zipFile)
try {
    $entry = $archive.GetEntry('MANIFEST.json')
    if (-not $entry) { throw 'This zip has no MANIFEST.json; it is not a StoryStudio Unified portable build.' }
    $reader = New-Object IO.StreamReader($entry.Open())
    try { $manifest = $reader.ReadToEnd() | ConvertFrom-Json } finally { $reader.Dispose() }
} finally { $archive.Dispose() }
if ($manifest.product -ne 'StoryStudio Unified portable' -or $manifest.version -notmatch '^[0-9][0-9A-Za-z.\-]{0,40}$') { throw 'Unexpected manifest contents.' }

$exports = Join-Path $StudioRoot 'exports'
New-Item -ItemType Directory -Force -Path $exports | Out-Null
$destination = Join-Path $exports ('unified-portable-' + $manifest.version)
if (Test-Path -LiteralPath $destination) { throw "$destination already exists. Nothing was changed; choose a different build or remove that folder yourself." }
$staging = Join-Path $exports ('.ups-' + [guid]::NewGuid().ToString('N').Substring(0, 8))
try {
    [IO.Compression.ZipFile]::ExtractToDirectory($zipFile, $staging)
    $bad = @()
    $count = 0
    foreach ($line in Get-Content -LiteralPath (Join-Path $staging 'SHA256SUMS.txt')) {
        if ($line -notmatch '^([A-Fa-f0-9]{64})  (.+)$') { continue }
        $count++
        $file = Join-Path $staging ($Matches[2] -replace '/', '\')
        if (-not (Test-Path -LiteralPath $file) -or (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash -ne $Matches[1].ToUpper()) { $bad += $Matches[2] }
    }
    if ($bad.Count -or $count -lt 1) { throw "File verification failed for $($bad.Count) file(s): $($bad[0..4] -join ', ')" }
    Move-Item -LiteralPath $staging -Destination $destination
} catch {
    if (Test-Path -LiteralPath $staging) { Remove-Item -LiteralPath $staging -Recurse -Force }  # only our own staging folder
    throw
}
$report = $destination + '.install-report.txt'
@(
    "StoryStudio Unified portable $($manifest.version)",
    "Installed (local time): $(Get-Date -Format s)",
    "Source zip: $zipFile",
    "Zip SHA-256: $actual (matched)",
    "Files verified against SHA256SUMS.txt: $count",
    "Installed to: $destination",
    "Start it with Open-StoryStudio-Unified-Portable.cmd"
) | Set-Content -LiteralPath $report -Encoding UTF8
Write-Output "INSTALLED: $destination ($count files verified)"
Write-Output "REPORT: $report"
