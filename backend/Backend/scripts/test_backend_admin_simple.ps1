param(
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [string]$Email = "admin@onee.ma"
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
        Write-Host "[ERREUR] $Name" -ForegroundColor Red
        Write-Host $_.Exception.Message -ForegroundColor Yellow

        if ($null -ne $_.ErrorDetails) {
            Write-Host $_.ErrorDetails.Message -ForegroundColor Yellow
        }

        return $null
    }
}

Write-Host ""
Write-Host "TEST BACKEND ONEE" -ForegroundColor Cyan
Write-Host "Serveur : $BaseUrl"
Write-Host "Compte  : $Email"
Write-Host ""

$health = Run-Test "Health" {
    Invoke-RestMethod `
        -Uri "$BaseUrl/api/v1/system/health" `
        -Method Get
}

if ($null -eq $health) {
    Write-Host ""
    Write-Host "Le serveur FastAPI ne repond pas." -ForegroundColor Red
    exit 1
}

$securePassword = Read-Host `
    "Mot de passe administrateur" `
    -AsSecureString

$pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR(
    $securePassword
)

try {
    $plainPassword = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
        $pointer
    )

    $login = Run-Test "Authentification" {
        Invoke-RestMethod `
            -Uri "$BaseUrl/api/v1/auth/login" `
            -Method Post `
            -ContentType "application/x-www-form-urlencoded" `
            -Body @{
                username = $Email
                password = $plainPassword
            }
    }
}
finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
    $plainPassword = $null
    $securePassword = $null
}

if (
    $null -eq $login -or
    [string]::IsNullOrWhiteSpace($login.access_token)
) {
    Write-Host ""
    Write-Host "Echec de connexion." -ForegroundColor Red
    exit 1
}

$headers = @{
    Authorization = "Bearer $($login.access_token)"
}

$me = Run-Test "Utilisateur connecte" {
    Invoke-RestMethod `
        -Uri "$BaseUrl/api/v1/auth/me" `
        -Method Get `
        -Headers $headers
}

if ($null -ne $me) {
    Write-Host "Email : $($me.email)"
    Write-Host "Role  : $($me.role)"
}

$dashboard = Run-Test "Dashboard" {
    Invoke-RestMethod `
        -Uri "$BaseUrl/api/v1/dashboard/summary" `
        -Method Get `
        -Headers $headers
}

$notifications = Run-Test "Notifications non lues" {
    Invoke-RestMethod `
        -Uri "$BaseUrl/api/v1/notifications/unread-count" `
        -Method Get `
        -Headers $headers
}

if ($null -ne $notifications) {
    Write-Host "Notifications : $($notifications.unread_count)"
}

$triageBody = @{
    description = "Ordinateur ne demarre plus et produit trois bips"
    equipment_code = "UC110955"
} | ConvertTo-Json

$triage = Run-Test "Triage IA" {
    Invoke-RestMethod `
        -Uri "$BaseUrl/api/v1/ai/triage" `
        -Method Post `
        -Headers $headers `
        -ContentType "application/json" `
        -Body $triageBody
}

if ($null -ne $triage) {
    Write-Host "Type       : $($triage.incident_type)"
    Write-Host "Groupe     : $($triage.classification_group)"
    Write-Host "Priorite   : $($triage.suggested_priority)"
    Write-Host "Confiance  : $($triage.confidence_score)"
}

$recurrent = Run-Test "Pannes recurrentes" {
    Invoke-RestMethod `
        -Uri "$BaseUrl/api/v1/ai/analytics/recurrent-failures?period_months=48&minimum_occurrences=3&limit=20" `
        -Method Get `
        -Headers $headers
}

if ($null -ne $recurrent) {
    Write-Host "Groupes recurrents : $($recurrent.total_groups)"
}

$stock = Run-Test "Risque de rupture du stock" {
    Invoke-RestMethod `
        -Uri "$BaseUrl/api/v1/ai/stock/shortage-risks?lookback_days=90&limit=100" `
        -Method Get `
        -Headers $headers
}

if ($null -ne $stock) {
    Write-Host "Pieces a risque : $($stock.total_at_risk)"
}

$equipmentId = docker exec maintenance_onee_db `
    psql `
    -U maintenance_app `
    -d maintenance_onee `
    -t `
    -A `
    -c "SELECT id FROM equipments WHERE code = 'UC110955' LIMIT 1;"

$equipmentId = (
    ($equipmentId | Select-Object -First 1) -as [string]
).Trim()

if ($equipmentId -match "^[0-9]+$") {
    $risk = Run-Test "Risque avance UC110955" {
        Invoke-RestMethod `
            -Uri "$BaseUrl/api/v1/ai/equipments/$equipmentId/risk-assessment" `
            -Method Get `
            -Headers $headers
    }

    if ($null -ne $risk) {
        Write-Host "Score  : $($risk.score)"
        Write-Host "Niveau : $($risk.level)"
    }
}
else {
    Write-Host "[IGNORE] UC110955 introuvable" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "TEST TERMINE" -ForegroundColor Cyan
