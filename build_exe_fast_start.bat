@echo off
REM ============================================================
REM  Alternative build: --onedir instead of --onefile.
REM  A --onedir build starts FASTER every time (no unpacking step),
REM  at the cost of producing a FOLDER (dist\BioSuite-NG\) instead
REM  of a single .exe file. Use this if startup speed matters more
REM  than having just one file to copy around.
REM ============================================================
cd /d "%~dp0"

python -m pip install -r requirements.txt
python -m pip install pyinstaller

pyinstaller --noconfirm --onedir --windowed ^
    --name BioSuite-NG ^
    --icon assets\biosuite_ng.ico ^
    --add-data "assets;assets" ^
    --add-data "data;data" ^
    --add-data "docs;docs" ^
    --collect-all PyQt6 ^
    --collect-all matplotlib ^
    --collect-all pydicom ^
    main.py

echo.
echo Done. Find BioSuite-NG.exe inside dist\BioSuite-NG\
echo Copy the WHOLE "BioSuite-NG" folder together -- the .exe needs the
echo other files next to it. Starts faster than the --onefile build.
pause
