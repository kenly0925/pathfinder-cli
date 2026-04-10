[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$CliArgs
)

$ErrorActionPreference = "Stop"
Push-Location $PSScriptRoot

try {
    $pythonExe = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"

    if (-not (Test-Path $pythonExe)) {
        Write-Host "Creating virtual environment..."
        if (Get-Command py -ErrorAction SilentlyContinue) {
            & py -3.11 -m venv .venv
        }
        else {
            & python -m venv .venv
        }

        if ($LASTEXITCODE -ne 0) {
            exit $LASTEXITCODE
        }
    }

    & $pythonExe -c "import rich, textual" *> $null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Installing package and dependencies..."
        & $pythonExe -m pip install -e .
        if ($LASTEXITCODE -ne 0) {
            exit $LASTEXITCODE
        }
    }

    if ($CliArgs.Count -eq 0) {
        $CliArgs = @("--login")
    }

    & $pythonExe -m pathfinder_cli @CliArgs
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
