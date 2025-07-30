:: start_project.bat
:: Starts the FastAPI server using Uvicorn for CryptoSDCA-AI within Anaconda prompt (Windows).
:: Use this script from the project root.

@echo off
REM start_project.bat - Windows batch launcher

echo 🔍 Checking Conda environment...
CALL conda activate cryptosdca
IF ERRORLEVEL 1 (
    echo Failed to activate conda environment
    pause
    exit /b 1
)

SET PROJECT_ROOT=%~dp0
SET PYTHONPATH=%PROJECT_ROOT%;%PYTHONPATH%

echo 📦 Installing dependencies...
pip install --upgrade pip
pip install https://github.com/cgohlke/talib-binary/releases/download/TA_Lib-0.4.28/TA_Lib-0.4.28-cp311-cp311-win_amd64.whl
pip install -r requirements.txt

echo 🗄️ Initializing database...
python scripts\init_db.py

echo 🚀 Starting server...
uvicorn "api.main:app" --reload --host 127.0.0.1 --port 8000
pause
