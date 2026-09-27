param(
    [string]$TaskName = "MaintIA-Daily-Failure-Forecast",
    [string]$DailyTime = "02:00",
    [int]$Limit = 1000
)

$ErrorActionPreference = "Stop"

$Backend = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Backend ".venv\Scripts\python.exe"
$Script = Join-Path $Backend "scripts\run_daily_failure_forecast.py"

if (-not (Test-Path $Python)) {
    throw "Python du venv introuvable : $Python"
}

if (-not (Test-Path $Script)) {
    throw "Script quotidien introuvable : $Script"
}

$At = [datetime]::ParseExact(
    $DailyTime,
    "HH:mm",
    [Globalization.CultureInfo]::InvariantCulture
)

$Action = New-ScheduledTaskAction `
    -Execute $Python `
    -Argument "`"$Script`" --horizon-days 90 --limit $Limit" `
    -WorkingDirectory $Backend

$Trigger = New-ScheduledTaskTrigger `
    -Daily `
    -At $At

$Settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 3)

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Description "Prediction quotidienne des risques de panne MaintIA ONEE" `
    -Force |
Out-Null

Write-Host "[OK] Tache planifiee : $TaskName" -ForegroundColor Green
Write-Host "Heure : $DailyTime"
Write-Host "Limite : $Limit equipements par execution"
