$ErrorActionPreference = "Stop"

if (-not (Test-Path ".venv")) {
    & "C:\Users\hp\AppData\Local\Programs\Python\Python312\python.exe" -m venv .venv
}

Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned -Force
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Le fichier .env a ete cree. Modifiez SECRET_KEY et le mot de passe admin." -ForegroundColor Yellow
}

python -m uvicorn app.main:app --reload --reload-dir app
