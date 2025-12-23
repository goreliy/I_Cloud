@echo off
chcp 65001 > nul
title Стресс-тест ThingSpeak Clone

echo ============================================================
echo   СТРЕСС-ТЕСТ - Запуск
echo ============================================================
echo.

REM Проверка Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python не найден!
    echo    Установите Python 3.8 или выше
    pause
    exit /b 1
)

REM Проверка файла
if not exist "run_stress_test.py" (
    echo ❌ Файл run_stress_test.py не найден!
    pause
    exit /b 1
)

REM Запуск
python run_stress_test.py

pause

