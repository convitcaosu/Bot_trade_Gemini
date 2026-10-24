@echo off
chcp 65001 >nul
echo ========================================
echo   BUILDING GEMINI TRADE BOT PRO v3.0
echo ========================================
echo.

:: Check if PyInstaller is installed
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo [*] Installing PyInstaller...
    pip install pyinstaller
)

echo [*] Building EXE (GeminiTradeBotPro)...
pyinstaller --noconfirm --onedir --windowed ^
    --name "GeminiTradeBotPro" ^
    --add-data "assets;assets" ^
    --add-data "bot_data;bot_data" ^
    --hidden-import "customtkinter" ^
    --hidden-import "PIL" ^
    --hidden-import "pandas" ^
    --hidden-import "matplotlib" ^
    --hidden-import "google.genai" ^
    --hidden-import "telebot" ^
    --hidden-import "MetaTrader5" ^
    --collect-all "customtkinter" ^
    main.py

echo.
echo ========================================
echo   BUILD COMPLETE!
echo   Output: dist\GeminiTradeBotPro\
echo   Run: dist\GeminiTradeBotPro\GeminiTradeBotPro.exe
echo   Hoac chay file: CHAY_APP.bat
echo ========================================
pause
