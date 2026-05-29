param(
    [string]$PythonVersion = "3.12",
    [string]$IndexUrl = "https://pypi.tuna.tsinghua.edu.cn/simple",
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$venvPath = Join-Path $repoRoot ".venv-test"
$configPath = Join-Path $repoRoot ".kt-test-home"
$pythonExe = Join-Path $venvPath "Scripts\\python.exe"

if (-not (Test-Path $venvPath)) {
    uv venv $venvPath --python $PythonVersion
}

if (-not (Test-Path $configPath)) {
    New-Item -ItemType Directory -Force $configPath | Out-Null
}

if (-not $SkipInstall) {
    Push-Location $repoRoot
    try {
        uv pip install --python $pythonExe --index-url $IndexUrl -e ".[dev]"
    }
    finally {
        Pop-Location
    }
}

Write-Output "Test environment ready."
Write-Output "python: $pythonExe"
Write-Output "kt-config-dir: $configPath"
Write-Output "mirror: $IndexUrl"
