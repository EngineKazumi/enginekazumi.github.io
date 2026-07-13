param(
    [string]$At = "09:00"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$TaskName = "FanboxSupporterUpdate"
$Runner = Join-Path $PSScriptRoot "update_and_publish.ps1"
$UserId = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$RunAt = [DateTime]::ParseExact($At, "HH:mm", [Globalization.CultureInfo]::InvariantCulture)

$Action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument ('-NoProfile -ExecutionPolicy Bypass -File "{0}"' -f $Runner) `
    -WorkingDirectory $PSScriptRoot
$Trigger = New-ScheduledTaskTrigger -Daily -At $RunAt
$Principal = New-ScheduledTaskPrincipal -UserId $UserId -LogonType Interactive -RunLevel Limited
$Settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1)

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Principal $Principal `
    -Settings $Settings `
    -Description "Update the FANBOX supporter list and push changed data to GitHub Pages." `
    -Force | Out-Null

$Info = Get-ScheduledTaskInfo -TaskName $TaskName
Write-Host ("Daily task registered. Next run: {0}" -f $Info.NextRunTime)
