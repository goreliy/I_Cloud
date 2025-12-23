#!/bin/bash

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функция для вывода сообщений
info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Проверка, что скрипт запущен из корня проекта
if [ ! -f "requirements.txt" ] || [ ! -f "run.py" ]; then
    error "Скрипт должен быть запущен из корня проекта!"
    exit 1
fi

info "=========================================="
info "IBolid Cloud - Скрипт запуска для Linux"
info "=========================================="
echo ""

# 1. Проверка Python
info "Проверка Python..."
if command -v python3.12 &> /dev/null; then
    PYTHON_CMD="python3.12"
    success "Python 3.12 найден"
elif command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
    PYTHON_CMD="python3"
    if [ "$PYTHON_VERSION" != "3.12" ]; then
        warning "Найден Python $PYTHON_VERSION, рекомендуется Python 3.12"
    else
        success "Python 3.12 найден"
    fi
else
    error "Python 3 не найден! Установите Python 3.12 или выше."
    exit 1
fi

# Проверка версии Python
PYTHON_VERSION_FULL=$($PYTHON_CMD --version 2>&1)
info "Используется: $PYTHON_VERSION_FULL"
echo ""

# 2. Проверка pip
info "Проверка pip..."
if ! $PYTHON_CMD -m pip --version &> /dev/null; then
    error "pip не найден! Установите pip для Python 3."
    info "Попытка установки pip через ensurepip..."
    $PYTHON_CMD -m ensurepip --upgrade || {
        error "Не удалось установить pip. Установите вручную:"
        info "  Debian/Ubuntu: sudo apt install python3-pip"
        info "  RHEL/CentOS: sudo dnf install python3-pip"
        info "  Alpine: sudo apk add py3-pip"
        exit 1
    }
fi
success "pip найден"
echo ""

# 3. Создание/активация виртуального окружения
info "Работа с виртуальным окружением..."
if [ ! -d "venv" ]; then
    info "Создание виртуального окружения..."
    $PYTHON_CMD -m venv venv --upgrade-deps || {
        error "Не удалось создать виртуальное окружение!"
        exit 1
    }
    success "Виртуальное окружение создано"
else
    success "Виртуальное окружение уже существует"
fi

# Активация venv
source venv/bin/activate || {
    error "Не удалось активировать виртуальное окружение!"
    exit 1
}

# Проверка, что активация прошла успешно
if [ -z "$VIRTUAL_ENV" ]; then
    error "Виртуальное окружение не активировано!"
    exit 1
fi

success "Виртуальное окружение активировано: $VIRTUAL_ENV"
echo ""

# 4. Обновление pip, setuptools, wheel
info "Обновление pip, setuptools, wheel..."
python -m pip install --upgrade pip setuptools wheel --quiet || {
    error "Не удалось обновить pip/setuptools/wheel"
    exit 1
}
success "Инструменты обновлены"
echo ""

# 5. Определение архитектуры
ARCH=$(uname -m)
info "Архитектура системы: $ARCH"

if [ "$ARCH" = "armv7l" ] || [ "$ARCH" = "armv6l" ]; then
    warning "Обнаружена ARM архитектура. Используем оптимизированную установку..."
    export PIP_PREFER_BINARY=1
    PIP_INSTALL_FLAGS="--no-build-isolation"
else
    PIP_INSTALL_FLAGS=""
fi
echo ""

# 6. Установка зависимостей
info "Установка зависимостей из requirements.txt..."
if [ -n "$PIP_INSTALL_FLAGS" ]; then
    python -m pip install $PIP_INSTALL_FLAGS -r requirements.txt || {
        error "Не удалось установить зависимости!"
        warning "Если проблема с psycopg2-binary на armv7, убедитесь что установлены dev-пакеты:"
        info "  Debian/Ubuntu: sudo apt install python3-dev build-essential libpq-dev"
        info "  RHEL/CentOS: sudo dnf install python3-devel gcc postgresql-devel"
        exit 1
    }
else
    python -m pip install -r requirements.txt || {
        error "Не удалось установить зависимости!"
        exit 1
    }
fi
success "Зависимости установлены"
echo ""

# 7. Проверка наличия .env файла
info "Проверка конфигурации..."
if [ ! -f ".env" ]; then
    warning "Файл .env не найден. Создаю из примера..."
    if [ -f "env.example" ]; then
        cp env.example .env
        success "Файл .env создан из env.example"
        warning "Отредактируйте .env перед запуском в production!"
    else
        warning "Файл env.example не найден. Создайте .env вручную."
    fi
else
    success "Файл .env найден"
fi
echo ""

# 8. Инициализация базы данных
info "Инициализация базы данных..."
python init_db.py || {
    error "Ошибка при инициализации базы данных!"
    exit 1
}
success "База данных инициализирована"
echo ""

# 9. Применение миграций Alembic
info "Применение миграций Alembic..."
if alembic current &> /dev/null; then
    info "Текущая версия БД: $(alembic current | head -n1)"
fi

# Проверка наличия новых миграций
if alembic heads &> /dev/null; then
    HEAD_REV=$(alembic heads | head -n1 | awk '{print $1}')
    CURRENT_REV=$(alembic current 2>/dev/null | head -n1 | awk '{print $1}' || echo "none")
    
    if [ "$CURRENT_REV" != "$HEAD_REV" ] && [ "$CURRENT_REV" != "none" ]; then
        info "Обнаружены новые миграции. Применение..."
        alembic upgrade head || {
            error "Ошибка при применении миграций!"
            exit 1
        }
        success "Миграции применены"
    else
        success "База данных актуальна (версия: ${CURRENT_REV:-none})"
    fi
else
    warning "Не удалось проверить миграции. Пропускаем..."
fi
echo ""

# 10. Проверка портов
info "Проверка доступности порта 8000..."
if command -v netstat &> /dev/null; then
    if netstat -tuln 2>/dev/null | grep -q ":8000 "; then
        warning "Порт 8000 уже занят!"
        info "Используется другим процессом или уже запущен сервер"
    else
        success "Порт 8000 свободен"
    fi
elif command -v ss &> /dev/null; then
    if ss -tuln 2>/dev/null | grep -q ":8000 "; then
        warning "Порт 8000 уже занят!"
    else
        success "Порт 8000 свободен"
    fi
else
    info "Не удалось проверить порт (netstat/ss не найдены)"
fi
echo ""

# 11. Финальная проверка
info "Проверка импорта основных модулей..."
python -c "from app.main import app; from app.config import settings; print('✓ Все модули загружены успешно')" || {
    error "Ошибка при импорте модулей приложения!"
    exit 1
}
success "Приложение готово к запуску"
echo ""

# 12. Вывод информации
info "=========================================="
info "Конфигурация:"
info "=========================================="
python -c "
from app.config import settings
print('  Приложение:', settings.APP_NAME)
print('  База данных:', settings.DATABASE_TYPE)
auth_status = 'Включена' if settings.AUTH_ENABLED else 'Отключена'
print('  Аутентификация:', auth_status)
debug_status = 'Включен' if settings.DEBUG else 'Выключен'
print('  Режим отладки:', debug_status)
print('  Воркеров:', settings.WORKERS)
if settings.AUTH_ENABLED:
    print('  Админ email:', settings.ADMIN_EMAIL)
    print('  Админ пароль:', settings.ADMIN_PASSWORD)
"
echo ""

# 13. Запуск приложения
info "=========================================="
success "Запуск сервера..."
info "=========================================="
info "Сервер будет доступен по адресу:"
info "  - http://localhost:8000"
info "  - http://0.0.0.0:8000 (извне)"
info "  - http://localhost:8000/docs (API документация)"
echo ""
info "Для остановки нажмите Ctrl+C"
echo ""

# Запуск приложения
python run.py

