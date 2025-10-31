@echo off
setlocal enabledelayedexpansion

REM Go to repo root
cd /d "%~dp0"

echo Starting CreditRater (auto-clean backend)…

REM Kill anything on 5051
for /f "tokens=5" %%a in ('netstat -ano ^| find ":5051" ^| find "LISTENING"') do (
  echo Killing existing backend on port 5051 (PID: %%a)…
  taskkill /PID %%a /F >NUL 2>NUL
)

REM Setup venv & deps
cd backend
if not exist .venv (
  echo Creating Python venv…
  python -m venv .venv
)

call .venv\Scripts\activate

echo Installing/validating Python dependencies…
python -m pip install --upgrade pip >NUL
pip install -r requirements.txt >NUL

echo Launching backend on http://127.0.0.1:5051 …
start "" /B python -m uvicorn server:app --host 127.0.0.1 --port 5051 --reload

timeout /t 1 >NUL
start "" "http://127.0.0.1:5051/app"

echo If the browser doesn't open, visit http://127.0.0.1:5051/app
