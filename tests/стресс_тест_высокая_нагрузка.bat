@echo off
chcp 65001 > nul
title Стресс-тест - Высокая нагрузка

echo ============================================================
echo   СТРЕСС-ТЕСТ - ВЫСОКАЯ НАГРУЗКА
echo ============================================================
echo   Параметры: 50 workers, 1000 RPS, 60 секунд
echo   Примерно 60,000 запросов
echo ============================================================
echo.
echo   ⚠️  ВНИМАНИЕ! Это создаст большую нагрузку на сервер!
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

set /p CONFIRM="Продолжить? (y/n): "
if /i not "%CONFIRM%"=="y" (
    echo Тест отменен
    pause
    exit /b 0
)

echo.
echo Запуск теста...
echo.

python tests/stress_test.py --api-key %API_KEY% --workers 50 --rps 1000 --duration 60

echo.
pause

