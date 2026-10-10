param([Parameter(Mandatory=$true)][string]$InputFile)
. (Join-Path $PSScriptRoot 'environment.ps1')
if(-not(Test-Path -LiteralPath $InputFile -PathType Leaf)){throw 'Input text file was not found'}
$taskOutput=Join-Path $env:STORY_STUDIO ('exports\narration-'+(Get-Date -Format 'yyyyMMdd-HHmmss')+'.wav')
& D:\StoryStudio\engine\.venv\Scripts\python.exe D:\StoryStudio\engine\narrate.py $InputFile --output $taskOutput
if($LASTEXITCODE -ne 0){throw 'Narration generation failed'}
