@echo off
d:
cd D:\projects\python\makeqandabyrohitjainaitool

if not exist .venv python -m venv .venv

echo [System] Activating local virtual environment...
call .venv\Scripts\activate

echo [System] Running dependency sync check...
pip install -r requirements.txt

echo [System] Starting FastAPI REST Server on port 8000...
echo [System] Swagger documentation will be available at http://127.0.0.1:8000/docs
uvicorn app.api:app --host 0.0.0.0 --port 8000 --reload

pause
