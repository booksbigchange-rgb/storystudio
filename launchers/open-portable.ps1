param([switch]$GuiTest)
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'environment.ps1')
$taskApp=Join-Path $env:STORY_STUDIO 'exports\portable-766646f\StoryStudio.exe'
if (-not (Test-Path -LiteralPath $taskApp)) {
    throw 'Extract the verified 766646f portable build into exports\portable-766646f first.'
}
if ($GuiTest) {
    $taskOutput=Join-Path $env:STORY_STUDIO ('exports\portable-local-validation-766646f\gui-'+(Get-Date -Format 'yyyyMMdd-HHmmss'))
    $taskArgs='--gui-test --output "'+$taskOutput+'"'
    $taskProcess=Start-Process -FilePath $taskApp -ArgumentList $taskArgs -WorkingDirectory (Split-Path $taskApp) -WindowStyle Hidden -PassThru
    if (-not $taskProcess.WaitForExit(180000)) { $taskProcess.Kill(); throw 'Portable GUI test timed out' }
    if ($taskProcess.ExitCode -ne 0) {
        Get-Content (Join-Path (Split-Path $taskApp) 'logs\portable-self-test.log')
        throw "Portable GUI test failed: $($taskProcess.ExitCode)"
    }
    Write-Output "PASS: local compiled GUI regression in $taskOutput"
} else {
    Start-Process -FilePath $taskApp -WorkingDirectory (Split-Path $taskApp)
}
