$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

Write-Host "[1/4] Generate NOTICE-004 samples"
Push-Location $Root
try {
    python .\validation\generate_stage7_samples.py

    Write-Host "[2/4] Run tests"
    python -m unittest discover -s tests -v
    if ($LASTEXITCODE -ne 0) { throw "Tests failed" }
}
finally {
    Pop-Location
}

Write-Host "[3/4] Check public schema count"
$Schemas = @(Get-ChildItem -LiteralPath (Join-Path $Root "schemas") -Filter '*.json' -File)
if ($Schemas.Count -ne 2) { throw "Expected two public schemas" }

Write-Host "[4/4] Check NOTICE-004 outputs"
$Outputs = @(Get-ChildItem -LiteralPath (Join-Path $Root "samples\outputs") -Filter 'NOTICE-004*.json' -File)
if ($Outputs.Count -ne 3) { throw "NOTICE-004 outputs are incomplete" }

Write-Host "Public sample validation passed." -ForegroundColor Green
