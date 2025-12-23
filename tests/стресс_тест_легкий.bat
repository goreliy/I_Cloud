@echo off
chcp 65001 > nul
title Легкий стресс-тест

echo ============================================================
echo   ЛЕГКИЙ СТРЕСС-ТЕСТ
echo ============================================================
echo   Параметры: 5 workers, 50 RPS, 30 секунд
echo   Примерно 1,500 запросов
echo ============================================================
echo.

REM Получить API ключ из БД
for /f "tokens=*" %%a in ('python -c "import sqlite3; conn=sqlite3.connect('ibolid.db'); result=conn.execute('SELECT key FROM api_keys WHERE type=\"write\" AND is_active=1 LIMIT 1').fetchone(); print(result[0] if result else '')"') do set API_KEY=%%a

if "%API_KEY%"=="" (
    echo ❌ Не найден активный Write API ключ!
    echo    Создайте канал через веб-интерфейс
    echo.
    pause
    exit /b 1
)

echo API ключ: %API_KEY%
echo.
echo Запуск теста...
echo.

python tests/stress_test.py --api-key %API_KEY% --workers 5 --rps 50 --duration 30

echo.
pause

