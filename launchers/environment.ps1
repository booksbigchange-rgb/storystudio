$env:STORY_STUDIO = 'D:\StoryStudio'
$env:TEMP = 'D:\StoryStudio\temp'
$env:TMP = $env:TEMP
$env:UV_CACHE_DIR = 'D:\StoryStudio\cache\uv'
$env:UV_PYTHON_CACHE_DIR = 'D:\StoryStudio\cache\python-downloads'
$env:UV_PYTHON_INSTALL_DIR = 'D:\StoryStudio\tools\python'
$env:UV_PYTHON_BIN_DIR = 'D:\StoryStudio\tools\python-bin'
$env:UV_TOOL_DIR = 'D:\StoryStudio\tools\uv-tools'
$env:UV_TOOL_BIN_DIR = 'D:\StoryStudio\tools\uv-tools-bin'
$env:PIP_CACHE_DIR = 'D:\StoryStudio\cache\pip'
$env:HF_HOME = 'D:\StoryStudio\cache\huggingface'
$env:TORCH_HOME = 'D:\StoryStudio\cache\torch'
$env:PYTHONPYCACHEPREFIX = 'D:\StoryStudio\cache\pycache'
$env:PYTHONNOUSERSITE = '1'
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:APPDATA = 'D:\StoryStudio\cache\profile\Roaming'
$env:USERPROFILE = 'D:\StoryStudio\cache\profile'
$env:LOCALAPPDATA = 'D:\StoryStudio\cache\profile\Local'
$env:XDG_CONFIG_HOME = 'D:\StoryStudio\cache\profile\config'
$env:XDG_CACHE_HOME = 'D:\StoryStudio\cache\profile\cache'
$env:XDG_DATA_HOME = 'D:\StoryStudio\cache\profile\data'
$env:SYNFIG_USER_SETTINGS = 'D:\StoryStudio\cache\profile\config\synfig'
$env:PATH = 'D:\StoryStudio\tools\ffmpeg;D:\StoryStudio\tools\uv;' + $env:PATH
foreach ($taskDirectory in @($env:TEMP,$env:UV_CACHE_DIR,$env:UV_PYTHON_CACHE_DIR,$env:UV_PYTHON_BIN_DIR,$env:APPDATA,$env:LOCALAPPDATA,$env:XDG_CONFIG_HOME,$env:XDG_CACHE_HOME,$env:XDG_DATA_HOME,$env:SYNFIG_USER_SETTINGS)) {
    New-Item -ItemType Directory -Path $taskDirectory -Force | Out-Null
}
