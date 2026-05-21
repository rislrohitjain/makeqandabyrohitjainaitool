@echo off
d:
cd D:\projects\python\makeqandabyrohitjainaitool

if not exist .venv python -m venv .venv

echo [System] Activating local virtual environment...
call .venv\Scripts\activate

echo [System] Running dependency sync check...
pip install -r requirements.txt

echo [System] Starting Streamlit interface...
streamlit run app/main.py

pause
