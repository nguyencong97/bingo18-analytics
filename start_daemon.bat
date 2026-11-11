@echo off
chcp 65001 >nul
title Bingo18 Pro - Autonomous Agent Daemon 24/7
color 0A

echo =====================================================================
echo           BINGO18 PRO - TOOL AGENT DAEMON TU DONG HOA 24/7
echo =====================================================================
echo [*] Khoi dong Agent Daemon tren IP Viet Nam...
echo [*] Tu dong kiem tra va PUSH du lieu moi sang Google Sheet
echo [*] Tu dong bao cao ket qua va nhan lenh qua Telegram (@bingo182026bot)
echo =====================================================================
echo.

if exist .venv\Scripts\python.exe (
    echo [>] Su dung Python trong moi truong ao .venv...
    .venv\Scripts\python.exe -m crawler.agent_daemon
) else (
    echo [>] Su dung Python he thong...
    python -m crawler.agent_daemon
)

pause
