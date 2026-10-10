param([ValidateSet('synfig','krita','kdenlive')][string]$Tool,[string]$Project)
. (Join-Path $PSScriptRoot 'environment.ps1')
$taskToolPaths=@{
    synfig='D:\StoryStudio\tools\synfig\bin\synfigstudio.exe'
    krita='D:\StoryStudio\tools\krita\krita-x64-5.3.4.1\bin\krita.exe'
    kdenlive='D:\StoryStudio\tools\kdenlive\kdenlive-26.08.1_standalone\bin\kdenlive.exe'
}
if(-not (Test-Path -LiteralPath $taskToolPaths[$Tool])){throw "Tool is missing: $Tool"}
if($Project){
    Start-Process -FilePath $taskToolPaths[$Tool] -ArgumentList ('"'+$Project+'"') -WorkingDirectory D:\StoryStudio
}else{
    Start-Process -FilePath $taskToolPaths[$Tool] -WorkingDirectory D:\StoryStudio
}
