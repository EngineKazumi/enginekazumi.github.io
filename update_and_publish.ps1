param(
    [switch]$NoPush
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectDir = [System.IO.Path]::GetFullPath((Split-Path -Parent $MyInvocation.MyCommand.Path))
$Python = Join-Path $ProjectDir ".venv\Scripts\python.exe"
$StateDir = Join-Path $env:LOCALAPPDATA "FanboxSupporterUpdater"
$LogDir = Join-Path $StateDir "logs"
$LogFile = Join-Path $LogDir "update.log"

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
if ((Test-Path $LogFile) -and (Get-Item $LogFile).Length -gt 1MB) {
    Move-Item -Force $LogFile (Join-Path $LogDir "update.previous.log")
}

function Write-Log {
    param([string]$Message)
    $line = "{0} {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    Write-Output $line
    Add-Content -LiteralPath $LogFile -Value $line -Encoding UTF8
}

function Invoke-Checked {
    param(
        [string]$Name,
        [scriptblock]$Command
    )
    & $Command
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0) {
        throw "$Name failed (exit code: $exitCode)"
    }
}

try {
    Set-Location $ProjectDir
    Write-Log "Starting update."
    Write-Log ("Project directory: " + $ProjectDir)

    if (-not (Test-Path $Python)) {
        throw "Python environment is missing. Run setup.ps1 first."
    }

    Invoke-Checked "FANBOX supporter retrieval" { & $Python (Join-Path $ProjectDir "fanboxWrite.py") }

    & git -C $ProjectDir diff --quiet -- "PatronName.txt"
    $diffExitCode = $LASTEXITCODE
    if ($diffExitCode -eq 0) {
        Write-Log "No changes. Nothing to push."
        exit 0
    }
    if ($diffExitCode -ne 1) {
        throw "git diff failed (exit code: $diffExitCode)"
    }

    if ($NoPush) {
        Write-Log "NoPush was specified. Nothing was pushed."
        exit 0
    }

    Invoke-Checked "git add" { git -C $ProjectDir add -- "PatronName.txt" }
    $message = "Auto update on {0}" -f (Get-Date -Format "yyyy-MM-dd")
    Invoke-Checked "git commit" { git -C $ProjectDir commit -m $message }
    Invoke-Checked "git push" { git -C $ProjectDir push origin HEAD:main }
    Write-Log "GitHub Pages data update completed."
    exit 0
}
catch {
    Write-Log ("ERROR: " + $_.Exception.Message)
    exit 1
}
