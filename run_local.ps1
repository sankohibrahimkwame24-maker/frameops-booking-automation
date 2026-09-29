$ErrorActionPreference = "Stop"
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
if (!(Test-Path .env)) { Copy-Item .env.example .env }
alembic upgrade head
uvicorn app.main:app --reload
