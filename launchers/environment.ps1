$env:STORY_STUDIO = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$env:TEMP = '$($env:STORY_STUDIO)\temp'
$env:TMP = $env:TEMP
$env:UV_CACHE_DIR = '$($env:STORY_STUDIO)\cache\uv'
$env:UV_PYTHON_CACHE_DIR = '$($env:STORY_STUDIO)\cache\python-downloads'
$env:UV_PYTHON_INSTALL_DIR = '$($env:STORY_STUDIO)\tools\python'
$env:UV_PYTHON_BIN_DIR = '$($env:STORY_STUDIO)\tools\python-bin'
$env:UV_TOOL_DIR = '$($env:STORY_STUDIO)\tools\uv-tools'
$env:UV_TOOL_BIN_DIR = '$($env:STORY_STUDIO)\tools\uv-tools-bin'
$env:PIP_CACHE_DIR = '$($env:STORY_STUDIO)\cache\pip'
$env:HF_HOME = '$($env:STORY_STUDIO)\cache\huggingface'
$env:TORCH_HOME = '$($env:STORY_STUDIO)\cache\torch'
$env:PYTHONPYCACHEPREFIX = '$($env:STORY_STUDIO)\cache\pycache'
$env:PYTHONNOUSERSITE = '1'
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:APPDATA = '$($env:STORY_STUDIO)\cache\profile\Roaming'
$env:USERPROFILE = '$($env:STORY_STUDIO)\cache\profile'
$env:LOCALAPPDATA = '$($env:STORY_STUDIO)\cache\profile\Local'
$env:XDG_CONFIG_HOME = '$($env:STORY_STUDIO)\cache\profile\config'
$env:XDG_CACHE_HOME = '$($env:STORY_STUDIO)\cache\profile\cache'
$env:XDG_DATA_HOME = '$($env:STORY_STUDIO)\cache\profile\data'
$env:SYNFIG_USER_SETTINGS = '$($env:STORY_STUDIO)\cache\profile\config\synfig'
$env:PATH = '$($env:STORY_STUDIO)\tools\ffmpeg;$($env:STORY_STUDIO)\tools\uv;' + $env:PATH
foreach ($taskDirectory in @($env:TEMP,$env:UV_CACHE_DIR,$env:UV_PYTHON_CACHE_DIR,$env:UV_PYTHON_BIN_DIR,$env:APPDATA,$env:LOCALAPPDATA,$env:XDG_CONFIG_HOME,$env:XDG_CACHE_HOME,$env:XDG_DATA_HOME,$env:SYNFIG_USER_SETTINGS)) {
    New-Item -ItemType Directory -Path $taskDirectory -Force | Out-Null
}
