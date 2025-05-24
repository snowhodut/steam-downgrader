@echo off
echo Installing required Python packages...

REM 파이썬이 설치되어 있고 PATH에 추가되어 있는지 확인
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo Python is not found in your PATH. Please install Python (and ensure it's added to PATH).
    pause
    exit /b 1
)

python -m pip install --upgrade pip
pip install -r requirements.txt

echo.
echo Installation complete.
pause