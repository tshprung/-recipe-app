@echo off
setlocal

set PYTHON="C:\Users\Tal\AppData\Local\Programs\Python\Python311\python.exe"

echo [1/4] Checking Python...
%PYTHON% --version || (echo ERROR: Python not found at expected path. & exit /b 1)

echo [2/4] Creating virtual environment...
%PYTHON% -m venv .venv

echo [3/4] Installing dependencies...
call .venv\Scripts\activate.bat
pip install -r requirements.txt

echo [4/4] Done.
echo.
echo To start the server:
echo   cd backend
echo   .venv\Scripts\activate
echo   uvicorn app.main:app --reload
