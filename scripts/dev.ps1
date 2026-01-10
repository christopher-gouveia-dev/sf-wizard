# Simple dev helper (no Docker).
# Starts API on :8000 and Web on :5173.

$root = Split-Path -Parent $PSScriptRoot

Write-Host "Starting API..."
Start-Process powershell -WorkingDirectory "$root\apps\api" -ArgumentList @(
  "-NoExit",
  "-Command",
  "python -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt; uvicorn sf_wizard.main:app --reload --host 127.0.0.1 --port 8000"
)

Write-Host "Starting Web..."
Start-Process powershell -WorkingDirectory "$root\apps\web" -ArgumentList @(
  "-NoExit",
  "-Command",
  "npm install; npm run dev"
)
