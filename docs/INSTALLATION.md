# Installation

## Backend

```powershell
cd 07_Developpement\Backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
docker start maintenance_onee_db
docker start maintenance_onee_qdrant
$env:PYTHONPATH = (Get-Location).Path
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

API :
`http://127.0.0.1:8000/docs`

## Frontend

```powershell
cd frontend_maintenance_onee_definitif_windows
npm install
Copy-Item .env.local.example .env.local
npm run dev
```

Application :
`http://localhost:3000`
