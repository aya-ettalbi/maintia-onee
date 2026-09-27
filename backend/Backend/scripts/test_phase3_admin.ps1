param(
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [string]$AdminEmail = "admin@onee.ma"
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

function Run-Test {
    param(
        [string]$Name,
        [scriptblock]$Action
    )

    try {
        $result = & $Action
        Write-Host "[OK] $Name" -ForegroundColor Green
        return $result
    }
    catch {
        Write-Host "[ECHEC] $Name" -ForegroundColor Red
        Write-Host $_.Exception.Message -ForegroundColor Yellow
        if ($_.ErrorDetails) {
            Write-Host $_.ErrorDetails.Message -ForegroundColor Yellow
        }
        return $null
    }
}

Write-Host ""
Write-Host "TEST PHASE 3 ONEE" -ForegroundColor Cyan
Write-Host "Serveur : $BaseUrl"
Write-Host "Compte  : $AdminEmail"
Write-Host ""

$health = Run-Test "Health" {
    Invoke-RestMethod `
        -Uri "$BaseUrl/api/v1/system/health" `
        -Method Get
}

if ($null -eq $health) {
    exit 1
}

$securePassword = Read-Host "Mot de passe administrateur" -AsSecureString
$pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword)

try {
    $plainPassword = [Runtime.InteropServices.Marshal]::PtrToStringAuto($pointer)
    $login = Run-Test "Authentification" {
        Invoke-RestMethod `
            -Uri "$BaseUrl/api/v1/auth/login" `
            -Method Post `
            -ContentType "application/x-www-form-urlencoded" `
            -Body @{
                username = $AdminEmail
                password = $plainPassword
            }
    }
}
finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
    $plainPassword = $null
    $securePassword = $null
}

if ($null -eq $login -or -not $login.access_token) {
    exit 1
}

$headers = @{
    Authorization = "Bearer $($login.access_token)"
}

$plans = Run-Test "Liste plans preventifs" {
    Invoke-RestMethod `
        -Uri "$BaseUrl/api/v1/preventive-maintenance/plans?limit=10" `
        -Method Get `
        -Headers $headers
}

$due = Run-Test "Echeances preventives" {
    Invoke-RestMethod `
        -Uri "$BaseUrl/api/v1/preventive-maintenance/due?days_ahead=30&limit=10" `
        -Method Get `
        -Headers $headers
}

$executions = Run-Test "Executions preventives" {
    Invoke-RestMethod `
        -Uri "$BaseUrl/api/v1/preventive-maintenance/executions?limit=10" `
        -Method Get `
        -Headers $headers
}

$kpi = Run-Test "KPI maintenance" {
    Invoke-RestMethod `
        -Uri "$BaseUrl/api/v1/kpi/maintenance?months=12" `
        -Method Get `
        -Headers $headers
}

if ($kpi) {
    Write-Host "Interventions      : $($kpi.total_interventions)"
    Write-Host "MTTR heures        : $($kpi.mttr_hours)"
    Write-Host "MTBF heures        : $($kpi.mtbf_hours)"
    Write-Host "Plans en retard    : $($kpi.overdue_preventive_plans)"
}

$now = Get-Date
$report = Run-Test "Rapport mensuel deterministe" {
    Invoke-RestMethod `
        -Uri "$BaseUrl/api/v1/reports/monthly?year=$($now.Year)&month=$($now.Month)" `
        -Method Get `
        -Headers $headers
}

$reports = Run-Test "Liste rapports generes" {
    Invoke-RestMethod `
        -Uri "$BaseUrl/api/v1/reports?limit=10" `
        -Method Get `
        -Headers $headers
}

Write-Host ""
Write-Host "Verification non destructive des routes d'ecriture..." -ForegroundColor Cyan

$fakeId = 999999999
$checks = @(
    @{
        Name = "GET plan inexistant retourne 404"
        Method = "Get"
        Url = "$BaseUrl/api/v1/preventive-maintenance/plans/$fakeId"
        Body = $null
    },
    @{
        Name = "PATCH plan inexistant retourne 404"
        Method = "Patch"
        Url = "$BaseUrl/api/v1/preventive-maintenance/plans/$fakeId"
        Body = @{ title = "Plan test" }
    },
    @{
        Name = "POST activate inexistant retourne 404"
        Method = "Post"
        Url = "$BaseUrl/api/v1/preventive-maintenance/plans/$fakeId/activate"
        Body = $null
    },
    @{
        Name = "POST deactivate inexistant retourne 404"
        Method = "Post"
        Url = "$BaseUrl/api/v1/preventive-maintenance/plans/$fakeId/deactivate"
        Body = $null
    },
    @{
        Name = "POST execute inexistant retourne 404"
        Method = "Post"
        Url = "$BaseUrl/api/v1/preventive-maintenance/plans/$fakeId/execute"
        Body = @{ technician_id = $null; estimated_cost = 0 }
    },
    @{
        Name = "GET KPI equipement inexistant retourne 404"
        Method = "Get"
        Url = "$BaseUrl/api/v1/kpi/equipments/$fakeId"
        Body = $null
    }
)

foreach ($check in $checks) {
    try {
        $params = @{
            Uri = $check.Url
            Method = $check.Method
            Headers = $headers
        }

        if ($null -ne $check.Body) {
            $params.ContentType = "application/json"
            $params.Body = ($check.Body | ConvertTo-Json -Depth 10)
        }

        Invoke-RestMethod @params | Out-Null
        Write-Host "[ECHEC] $($check.Name)" -ForegroundColor Red
    }
    catch {
        $statusCode = 0
        try {
            $statusCode = [int]$_.Exception.Response.StatusCode
        }
        catch {
        }

        if ($statusCode -eq 404) {
            Write-Host "[OK] $($check.Name)" -ForegroundColor Green
        }
        else {
            Write-Host "[ECHEC] $($check.Name) : HTTP $statusCode" `
                -ForegroundColor Red
        }
    }
}

Write-Host ""
Write-Host "TEST PHASE 3 TERMINE" -ForegroundColor Cyan
