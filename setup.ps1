param(
    [switch]$SkipDependencies
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$Python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not $SkipDependencies) {
    if (-not (Test-Path $Python)) {
        py -3.13 -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw "Failed to create the Python virtual environment." }
    }

    & $Python -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) { throw "Failed to update pip." }
    & $Python -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw "Failed to install Selenium." }
}

Write-Host "Setup completed. Run setup_login.bat and sign in to FANBOX."
