@echo off
rem Builds MiniIsland.exe (no Python needed on the target PC).
rem Run run.bat once first, so that .venv with all dependencies exists.
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo .venv not found. Run run.bat first.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m pip install pyinstaller || goto :err
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --windowed --name MiniIsland --icon MiniIsland.ico ^
  --collect-all comtypes --collect-all pycaw ^
  --collect-all winrt.runtime --collect-all winrt.windows.foundation ^
  --collect-all winrt.windows.foundation.collections --collect-all winrt.windows.storage.streams ^
  --collect-all winrt.windows.media.control --collect-all winrt.windows.graphics.imaging ^
  --collect-all winrt.windows.media.ocr --collect-all winrt.windows.globalization ^
  --collect-all cv2 --collect-all mss ^
  island.py || goto :err
echo.
echo Done: dist\MiniIsland\MiniIsland.exe
echo Next step (installer): open installer.iss in Inno Setup and press Compile.
pause
exit /b 0
:err
echo Build failed.
pause
