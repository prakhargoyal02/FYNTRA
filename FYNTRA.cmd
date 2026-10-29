@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" goto existing
py -3.13 -c "import sys" >nul 2>&1
if not errorlevel 1 goto py313
py -3.12 -c "import sys" >nul 2>&1
if not errorlevel 1 goto py312
python -c "import sys; sys.exit(0 if sys.version_info[:2] in [(3,12),(3,13)] else 1)" >nul 2>&1
if not errorlevel 1 goto generic
 echo Install Python 3.13 or 3.12 from https://www.python.org/downloads/
 echo Enable the Python launcher or Add Python to PATH during installation.
 echo Then open this folder again and run START_FYNTRA.cmd.
 pause
 exit /b 1
:existing
".venv\Scripts\python.exe" "tools\manage.py" %*
goto done
:py313
py -3.13 "tools\manage.py" %*
goto done
:py312
py -3.12 "tools\manage.py" %*
goto done
:generic
python "tools\manage.py" %*
:done
set "FYNTRA_RESULT=%errorlevel%"
if not "%FYNTRA_RESULT%"=="0" pause
exit /b %FYNTRA_RESULT%
