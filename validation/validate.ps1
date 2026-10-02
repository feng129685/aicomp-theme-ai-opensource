$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$expectedSchemaHashes = @(
    '96A5019EEC822AC62BA12C7666A599F9084C1E2D5A2480E0BF06462CF6622702',
    'A56C22A84D9B847301EBAC40AB034ED89F8B345F62EA1934ADE3D94C1A02622A'
) | Sort-Object

Push-Location $root
try {
    python -m unittest discover -s tests -v
    if ($LASTEXITCODE -ne 0) { throw '单元测试失败' }
    python cli.py self-check
    if ($LASTEXITCODE -ne 0) { throw 'CLI 自检失败' }
    python validation\validate.py
    if ($LASTEXITCODE -ne 0) { throw '生成输出核验失败' }

    $localSchemas = @(Get-ChildItem -Path (Join-Path $root 'schemas') -Filter '*.json' -File | Get-FileHash -Algorithm SHA256)
    if ($localSchemas.Count -ne 2) { throw 'Expected exactly two frozen schema files' }
    $localHashes = @($localSchemas.Hash | Sort-Object)
    if (Compare-Object $localHashes $expectedSchemaHashes) { throw 'Frozen schema hashes differ from the published contract' }
    foreach ($hash in $localHashes) { Write-Host "PASS frozen schema SHA256: $hash" }
    Write-Host 'Validation passed.'
} finally {
    Pop-Location
}
