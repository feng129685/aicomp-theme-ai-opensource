$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Push-Location $root
try {
    python -m unittest tests.test_sync_fixtures -v
    if ($LASTEXITCODE -ne 0) { throw "Sync fixture tests failed" }
    python validation/validate_sync_fixtures.py
    if ($LASTEXITCODE -ne 0) { throw "Sync fixture validation failed" }
    Write-Host "Sync fixture validation passed." -ForegroundColor Green
}
finally {
    Pop-Location
}
