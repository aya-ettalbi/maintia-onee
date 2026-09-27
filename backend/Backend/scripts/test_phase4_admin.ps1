param(
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [string]$AdminEmail = "admin@onee.ma",
    [switch]$UseLLM
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
Write-Host "TEST PHASE 4 - PREDICTION IA DES PANNES" -ForegroundColor Cyan
Write-Host "Serveur : $BaseUrl"
Write-Host "Compte  : $AdminEmail"
Write-Host "LLM     : $UseLLM"
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

$equipmentId = docker exec maintenance_onee_db `
    psql `
    -U maintenance_app `
    -d maintenance_onee `
    -t `
    -A `
    -c @"
SELECT e.id
FROM equipments e
JOIN equipment_historical_links l ON l.equipment_id = e.id
WHERE e.archived = false
GROUP BY e.id
ORDER BY COUNT(*) DESC, e.id
LIMIT 1;
"@

$equipmentId = (($equipmentId | Select-Object -First 1) -as [string]).Trim()

if (-not ($equipmentId -match "^[0-9]+$")) {
    Write-Host "[ECHEC] Aucun equipement lie a l'historique." -ForegroundColor Red
    exit 1
}

Write-Host "Equipement test : $equipmentId"

$llmValue = if ($UseLLM) { "true" } else { "false" }

$forecast = Run-Test "Creation prevision individuelle" {
    Invoke-RestMethod `
        -Uri "$BaseUrl/api/v1/ai/failure-forecasts/equipments/${equipmentId}?horizon_days=90&use_llm=$llmValue&create_actions=false" `
        -Method Post `
        -Headers $headers
}

if ($forecast) {
    Write-Host "Forecast ID       : $($forecast.id)"
    Write-Host "Score              : $($forecast.risk_score)"
    Write-Host "Probabilite        : $($forecast.failure_probability)"
    Write-Host "Calibree           : $($forecast.probability_calibrated)"
    Write-Host "Niveau             : $($forecast.risk_level)"
    Write-Host "Confiance preuves  : $($forecast.evidence_confidence)"
    Write-Host "Famille            : $($forecast.predicted_failure_family)"
    Write-Host "LLM utilise        : $($forecast.llm_used)"
    Write-Host "Modele             : $($forecast.model_name)"
}

Run-Test "Derniere prevision equipement" {
    Invoke-RestMethod `
        -Uri "$BaseUrl/api/v1/ai/failure-forecasts/equipments/$equipmentId/latest" `
        -Method Get `
        -Headers $headers
} | Out-Null

Run-Test "Historique previsions equipement" {
    Invoke-RestMethod `
        -Uri "$BaseUrl/api/v1/ai/failure-forecasts/equipments/$equipmentId/history?limit=10" `
        -Method Get `
        -Headers $headers
} | Out-Null

Run-Test "Liste risques eleves" {
    Invoke-RestMethod `
        -Uri "$BaseUrl/api/v1/ai/failure-forecasts/high-risk?limit=20" `
        -Method Get `
        -Headers $headers
} | Out-Null

$summary = Run-Test "Synthese previsions" {
    Invoke-RestMethod `
        -Uri "$BaseUrl/api/v1/ai/failure-forecasts/summary" `
        -Method Get `
        -Headers $headers
}

if ($summary) {
    Write-Host "Previsions totales : $($summary.total_forecasts)"
    Write-Host "Risques HIGH        : $($summary.high_risk)"
    Write-Host "A valider           : $($summary.pending_validation)"
}

Run-Test "Liste executions batch" {
    Invoke-RestMethod `
        -Uri "$BaseUrl/api/v1/ai/failure-forecast-runs?limit=10" `
        -Method Get `
        -Headers $headers
} | Out-Null

Write-Host ""
Write-Host "Verification non destructive des erreurs..." -ForegroundColor Cyan

$fakeId = 999999999

try {
    Invoke-RestMethod `
        -Uri "$BaseUrl/api/v1/ai/failure-forecasts/equipments/${fakeId}?horizon_days=90&use_llm=false" `
        -Method Post `
        -Headers $headers |
    Out-Null

    Write-Host "[ECHEC] Equipement inexistant devait retourner 404" `
        -ForegroundColor Red
}
catch {
    $statusCode = 0
    try {
        $statusCode = [int]$_.Exception.Response.StatusCode
    }
    catch {
    }

    if ($statusCode -eq 404) {
        Write-Host "[OK] Equipement inexistant retourne 404" `
            -ForegroundColor Green
    }
    else {
        Write-Host "[ECHEC] Equipement inexistant : HTTP $statusCode" `
            -ForegroundColor Red
    }
}

try {
    Invoke-RestMethod `
        -Uri "$BaseUrl/api/v1/ai/failure-forecasts/$fakeId/validate" `
        -Method Patch `
        -Headers $headers `
        -ContentType "application/json" `
        -Body (@{
            validation_status = "REJECTED"
            notes = "Test"
        } | ConvertTo-Json) |
    Out-Null

    Write-Host "[ECHEC] Prevision inexistante devait retourner 404" `
        -ForegroundColor Red
}
catch {
    $statusCode = 0
    try {
        $statusCode = [int]$_.Exception.Response.StatusCode
    }
    catch {
    }

    if ($statusCode -eq 404) {
        Write-Host "[OK] Prevision inexistante retourne 404" `
            -ForegroundColor Green
    }
    else {
        Write-Host "[ECHEC] Prevision inexistante : HTTP $statusCode" `
            -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "TEST PHASE 4 TERMINE" -ForegroundColor Cyan
