# Run from the project folder in Windows PowerShell.
$ErrorActionPreference = 'Stop'
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m job_rag.ingest
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m job_rag.evaluate
Write-Host "Setup complete. Start API with: .\.venv\Scripts\uvicorn.exe job_rag.api:app --reload"
