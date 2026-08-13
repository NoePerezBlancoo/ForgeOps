$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Python = Join-Path $RepoRoot ".ai\.venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $Python)) {
    & (Join-Path $PSScriptRoot "install-forgeops-agent.ps1")
}

Push-Location $RepoRoot
try {
    & $Python -m forgeops_agent.cli @args
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}

