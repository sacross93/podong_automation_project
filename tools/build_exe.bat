@echo off
setlocal enabledelayedexpansion

rem Simple batch wrapper for packaging via flet pack
set NAME=PodongApp
set ICON=

if not exist main.py (
  echo [ERROR] main.py not found. Run from project root.
  exit /b 1
)

where flet >nul 2>nul
if errorlevel 1 (
  echo [ERROR] flet CLI not found. Activate your venv and run: pip install "flet[all]" pyinstaller
  exit /b 1
)

set CMD=flet pack .\main.py --name "%NAME%" --onefile --windowed

if defined ICON (
  set CMD=%CMD% --icon "%ICON%"
)

if exist exception_list.json (
  set CMD=%CMD% --add-data "exception_list.json;."
)

if exist src\ui (
  set CMD=%CMD% --add-data "src\ui;src\ui"
)

echo %CMD%
%CMD%

if errorlevel 1 (
  echo [ERROR] Packaging failed.
  exit /b 1
)

echo Done. See .\dist\%NAME%.exe

endlocal

