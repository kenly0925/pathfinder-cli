[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$CliArgs
)

if ($CliArgs.Count -eq 0) {
    $CliArgs = @("--login")
}

& "$PSScriptRoot\dev.ps1" @CliArgs
exit $LASTEXITCODE
