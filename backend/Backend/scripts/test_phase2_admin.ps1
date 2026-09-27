param(
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [string]$AdminEmail = "admin@onee.ma"
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

function Show-Test {
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
Write-Host "TEST PHASE 2 ONEE" -ForegroundColor Cyan
Write-Host "Serveur : $BaseUrl"
Write-Host "Compte  : $AdminEmail"
Write-Host ""

$health = Show-Test "Health" {
    Invoke-RestMethod `
        -Uri "$BaseUrl/api/v1/system/health" `
        -Method Get
}

if ($null -eq $health) {
    Write-Host "Demarrez FastAPI dans un autre terminal." -ForegroundColor Red
    exit 1
}

$securePassword = Read-Host "Mot de passe administrateur" -AsSecureString
$pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword)

try {
    $plainPassword = [Runtime.InteropServices.Marshal]::PtrToStringAuto($pointer)

    $login = Show-Test "Authentification" {
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

$summary = Show-Test "Stock summary" {
    Invoke-RestMethod `
        -Uri "$BaseUrl/api/v1/stock/summary" `
        -Method Get `
        -Headers $headers
}

if ($summary) {
    Write-Host "Total pieces      : $($summary.total_parts)"
    Write-Host "Pieces actives    : $($summary.active_parts)"
    Write-Host "Quantite totale   : $($summary.total_quantity)"
    Write-Host "Stock faible      : $($summary.low_stock_parts)"
    Write-Host "Ruptures          : $($summary.out_of_stock_parts)"
    Write-Host "Valeur inventaire : $($summary.inventory_value)"
}

$alerts = Show-Test "Stock alerts" {
    Invoke-RestMethod `
        -Uri "$BaseUrl/api/v1/stock/alerts?limit=100" `
        -Method Get `
        -Headers $headers
}

if ($alerts) {
    Write-Host "Alertes stock : $($alerts.total)"
}

Write-Host ""
Write-Host "Verification non destructive des routes d'ecriture..." -ForegroundColor Cyan

$fakeIntervention = 999999999
$fakeItem = 999999999

$checks = @(
    @{
        Name = "PATCH action retourne 404"
        Method = "Patch"
        Url = "$BaseUrl/api/v1/interventions/$fakeIntervention/actions/$fakeItem"
        Body = @{ description = "Action de verification" }
    },
    @{
        Name = "DELETE action retourne 404"
        Method = "Delete"
        Url = "$BaseUrl/api/v1/interventions/$fakeIntervention/actions/$fakeItem"
        Body = $null
    },
    @{
        Name = "PATCH part retourne 404"
        Method = "Patch"
        Url = "$BaseUrl/api/v1/interventions/$fakeIntervention/parts/$fakeItem"
        Body = @{ quantity = 2 }
    },
    @{
        Name = "DELETE part retourne 404"
        Method = "Delete"
        Url = "$BaseUrl/api/v1/interventions/$fakeIntervention/parts/$fakeItem"
        Body = $null
    },
    @{
        Name = "POST close retourne 404"
        Method = "Post"
        Url = "$BaseUrl/api/v1/interventions/$fakeIntervention/close"
        Body = @{
            diagnosis = "Diagnostic test"
            solution = "Solution test"
            test_result = "OK"
            comment = "Test non destructif"
        }
    },
    @{
        Name = "POST cancel retourne 404"
        Method = "Post"
        Url = "$BaseUrl/api/v1/interventions/$fakeIntervention/cancel"
        Body = @{ reason = "Test non destructif" }
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
        Write-Host "[ECHEC] $($check.Name) : la route n'a pas retourne 404" `
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
            Write-Host "[OK] $($check.Name)" -ForegroundColor Green
        }
        else {
            Write-Host "[ECHEC] $($check.Name) : HTTP $statusCode" `
                -ForegroundColor Red
        }
    }
}

Write-Host ""
Write-Host "TEST PHASE 2 TERMINE" -ForegroundColor Cyan
