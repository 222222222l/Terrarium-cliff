param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$CommandArgs
)

$ErrorActionPreference = "Stop"

if (-not $CommandArgs -or $CommandArgs.Count -eq 0) {
    throw "Usage: .\scripts\run-in-test-env.ps1 <command> [args...]"
}

$repoRoot = Split-Path -Parent $PSScriptRoot
$venvPath = Join-Path $repoRoot ".venv-test"
$venvScripts = Join-Path $venvPath "Scripts"
$configPath = Join-Path $repoRoot ".kt-test-home"

if (-not (Test-Path $venvPath)) {
    throw "Missing .venv-test. Run .\scripts\setup-test-env.ps1 first."
}

if (-not (Test-Path $configPath)) {
    New-Item -ItemType Directory -Force $configPath | Out-Null
}

$env:VIRTUAL_ENV = $venvPath
$env:KT_CONFIG_DIR = $configPath
$env:PATH = "$venvScripts;$env:PATH"

$command = $CommandArgs[0]
$args = @()
if ($CommandArgs.Count -gt 1) {
    $args = $CommandArgs[1..($CommandArgs.Count - 1)]
}

Push-Location $repoRoot
try {
    & $command @args
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
