param([switch]$SandboxFixtures)
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\environment.ps1"
$verificationArguments = @()
if ($SandboxFixtures) { $verificationArguments += '--sandbox-fixtures' }
& "$env:STORY_STUDIO\engine\.venv\Scripts\python.exe" "$env:STORY_STUDIO\tests\verify_mvp.py" @verificationArguments
exit $LASTEXITCODE
