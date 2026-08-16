@echo off
REM BharatBuild CLI — Windows Installer
echo.
echo   BharatBuild CLI Installer
echo   =========================
echo.

REM Check Python
python --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo   ERROR: Python not found. Install Python 3.10+ from python.org
    pause
    exit /b 1
)

SET VENV_DIR=%USERPROFILE%\.bharatbuild\venv

IF NOT EXIST "%VENV_DIR%" (
    echo   Creating virtualenv at %VENV_DIR% ...
    python -m venv "%VENV_DIR%"
)

CALL "%VENV_DIR%\Scripts\activate.bat"

echo   Installing dependencies ...
pip install --quiet --upgrade pip
pip install --quiet -r "%~dp0requirements.txt"

echo   Installing bharatbuild CLI ...
pip install --quiet -e "%~dp0.."

REM Create a wrapper batch file in user Scripts
SET SCRIPTS_DIR=%VENV_DIR%\Scripts
echo @echo off > "%SCRIPTS_DIR%\bharatbuild.bat"
echo CALL "%SCRIPTS_DIR%\activate.bat" >> "%SCRIPTS_DIR%\bharatbuild.bat"
echo python -m cli.main %%* >> "%SCRIPTS_DIR%\bharatbuild.bat"

echo.
echo   Done!
echo   Add %SCRIPTS_DIR% to your PATH, then run:  bharatbuild login
echo.
pause
