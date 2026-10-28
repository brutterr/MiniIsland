@echo off
cd /d "%~dp0"
if not exist ".venv\installed2.flag" (
  echo First run: installing dependencies, please wait...
  python -m venv .venv || goto :err
  ".venv\Scripts\python.exe" -m pip install --upgrade pip
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt || goto :err
  echo Installing extras: OCR, QR, screen recording, volume...
  ".venv\Scripts\python.exe" -m pip install -r requirements-extra.txt || echo WARNING: some extras failed, those buttons will not work
  echo ok> ".venv\installed2.flag"
)
start "" ".venv\Scripts\pythonw.exe" island.py
exit /b 0
:err
echo.
echo Install failed. Make sure Python 3.10+ is installed and added to PATH.
pause
