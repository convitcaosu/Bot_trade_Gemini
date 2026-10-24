@echo off
chcp 65001 >nul
title Khởi Động Gemini Trade Bot Pro v3.0

if exist "%~dp0dist\GeminiTradeBotPro\GeminiTradeBotPro.exe" (
    start "" "%~dp0dist\GeminiTradeBotPro\GeminiTradeBotPro.exe"
    exit
) else if exist "%~dp0dist\GeminiTradeBot\GeminiTradeBot.exe" (
    start "" "%~dp0dist\GeminiTradeBot\GeminiTradeBot.exe"
    exit
) else (
    echo [*] Đang khởi động trực tiếp bằng Python...
    start "" python "%~dp0main.py"
    exit
)
