@echo off
REM ============================================================
REM  Build a standalone BioSuite-NG.exe (no Python install needed
REM  afterwards) using PyInstaller. Run this ONCE on your Windows
REM  machine (with Python + requirements.txt already installed).
REM  The .exe will appear in the "dist" folder, using the AJUMS
REM  Medical Physics Research Group logo as its icon.
REM
REM  --splash shows the logo INSTANTLY on double-click, drawn by the
REM  bootloader itself before Python even starts -- this specifically
REM  fixes the "nothing happens for several seconds" startup complaint
REM  for --onefile builds (see main.py's pyi_splash handling).
REM ============================================================
cd /d "%~dp0"

python -m pip install -r requirements.txt
python -m pip install pyinstaller

pyinstaller --noconfirm --onefile --windowed ^
    --name BioSuite-NG ^
    --icon assets\biosuite_ng.ico ^
    --splash assets\logo_square.png ^
    --add-data "assets;assets" ^
    --add-data "data;data" ^
    --add-data "docs;docs" ^
    --collect-all PyQt6 ^
    --collect-all matplotlib ^
    --collect-all pydicom ^
    main.py

echo.
echo Done. Find BioSuite-NG.exe inside the "dist" folder.
echo You can copy dist\BioSuite-NG.exe anywhere and double-click it directly.
echo The AJUMS logo now appears the instant you double-click it.
pause
