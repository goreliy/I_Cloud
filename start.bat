@echo off
chcp 65001 >nul
echo Инициализация базы данных...
python init_db.py
if %ERRORLEVEL% EQU 0 (
    echo.
    echo Применение миграций...
    alembic stamp head
    echo.
    echo ===================================
    echo База данных готова!
    echo Запускаем сервер...
    echo ===================================
    echo.
    python run.py
) else (
    echo.
    echo Ошибка при инициализации базы данных!
    pause
)

