$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Push-Location $root
try {
    python -m unittest discover -s tests -v
    if ($LASTEXITCODE -ne 0) { throw 'Stage 6 tests failed' }
    python cli.py self-check
    if ($LASTEXITCODE -ne 0) { throw 'CLI self-check failed' }
    $recordText = Get-Content -Raw -Encoding utf8 'samples\outputs\easyocr-real-run.json'
    $record = $recordText | ConvertFrom-Json
    if ($record.engine -ne 'EasyOCR' -or $record.engine_version -ne '1.7.2') { throw 'Real engine metadata incomplete' }
    if ($record.PSObject.Properties.Name -notcontains 'error_type' -or [string]::IsNullOrWhiteSpace([string]$record.error_type)) {
        throw 'Real engine run must include an error type'
    }
    # Keep this check textual: Windows PowerShell may coerce JSON null into an
    # empty value, and measured_accuracy is optional in older run records.
    if ($recordText -notmatch '"accuracy"\s*:\s*null') { throw 'Accuracy must remain null when engine run is incomplete' }
    if ($record.PSObject.Properties.Name -contains 'measured_accuracy' -and $record.measured_accuracy -ne $false) {
        throw 'measured_accuracy must be false when engine run is incomplete'
    }
    Write-Host 'PASS EasyOCR real-run record: accuracy remains null'
    Write-Host 'Stage 6 validation passed.'
} finally {
    Pop-Location
}
