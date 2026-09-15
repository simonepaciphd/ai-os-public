[CmdletBinding()]
param([ValidateSet('codex-cli','claude-code')][string]$Harness)
$ErrorActionPreference = 'Stop'
try {
    $installRoot = Split-Path -Parent $PSScriptRoot
    $configuration = Get-Content -Raw -LiteralPath (Join-Path $installRoot 'config/ownership.json') | ConvertFrom-Json
    & $configuration.python_executable -I -B (Join-Path $PSScriptRoot 'aios.py') --harness $Harness
    exit $LASTEXITCODE
} catch {
    [Console]::Error.WriteLine('AI OS hook launcher failed; inspect the installation. Close unconfirmed.')
    Write-Output '{"continue":false,"stopReason":"AI OS hook launcher failed"}'
    exit 2
}
