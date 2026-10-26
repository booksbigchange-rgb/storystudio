<#
Downloads FFmpeg from an official source linked by ffmpeg.org, verifies the publisher's SHA-256, and installs
ffmpeg.exe/ffprobe.exe into -Destination. Tries gyan.dev first, then BtbN's builds (retrying each), and records
the URL, checksum and version in -Provenance. Fails if no source can be verified.
#>
param(
    [string]$Destination = 'tools/ffmpeg',
    [string]$Provenance = 'artifacts/ffmpeg-provenance.json',
    [string]$Work = 'temp'
)
$ErrorActionPreference = 'Stop'
New-Item -Force -ItemType Directory $Destination, $Work, (Split-Path $Provenance) | Out-Null

function Fetch([string]$Url, [string]$Out) {
    for ($attempt = 1; $attempt -le 4; $attempt++) {
        try { Invoke-WebRequest $Url -OutFile $Out -TimeoutSec 900; return }
        catch { if ($attempt -eq 4) { throw }; Write-Warning "Download attempt $attempt failed for $Url : $_"; Start-Sleep -Seconds (20 * $attempt) }
    }
}

$sources = @(
    @{ Name = 'gyan.dev release essentials'; Zip = 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip'; Sums = 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip.sha256'; File = 'ffmpeg-release-essentials.zip' },
    @{ Name = 'BtbN FFmpeg-Builds win64 gpl'; Zip = 'https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip'; Sums = 'https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/checksums.sha256'; File = 'ffmpeg-master-latest-win64-gpl.zip' }
)
foreach ($source in $sources) {
    try {
        $zip = Join-Path $Work $source.File
        $sums = Join-Path $Work ($source.File + '.sums')
        $unpacked = Join-Path $Work ('ffmpeg-' + [guid]::NewGuid().ToString('N').Substring(0, 8))
        Fetch $source.Zip $zip
        Fetch $source.Sums $sums
        $published = $null
        $all = @(Get-Content $sums)
        foreach ($line in $all) {
            if ($line -match '([A-Fa-f0-9]{64})') {
                $candidate = $Matches[1].ToUpper()
                if ($all.Count -eq 1 -or $line.Contains($source.File)) { $published = $candidate; break }
            }
        }
        if (-not $published) { throw 'No published checksum found' }
        $actual = (Get-FileHash $zip -Algorithm SHA256).Hash
        if ($actual -ne $published) { throw "Checksum mismatch: published $published, got $actual" }
        Expand-Archive $zip $unpacked
        foreach ($name in @('ffmpeg.exe', 'ffprobe.exe')) {
            $binary = Get-ChildItem $unpacked -Recurse -Filter $name | Select-Object -First 1
            if (-not $binary) { throw "Missing $name" }
            Copy-Item $binary.FullName $Destination -Force
        }
        $root = (Get-ChildItem $unpacked -Directory | Select-Object -First 1).FullName
        if ($env:GITHUB_ENV) { "FFMPEG_LICENSE_ROOT=$root" | Add-Content -Path $env:GITHUB_ENV }
        $version = (& (Join-Path $Destination 'ffmpeg.exe') -version | Select-Object -First 1)
        @{ source = $source.Name; url = $source.Zip; sha256 = $actual; publisher_checksum_verified = $true; version = $version } | ConvertTo-Json | Set-Content $Provenance -Encoding UTF8
        Write-Output "FFmpeg installed from $($source.Name): $version"
        return
    } catch {
        Write-Warning "$($source.Name) could not be used: $_"
    }
}
throw 'No official FFmpeg source could be downloaded and verified'
