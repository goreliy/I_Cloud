# Запуск на Linux

## Быстрый старт

1. Сделайте скрипт исполняемым:
```bash
chmod +x start.sh
```

2. Запустите скрипт:
```bash
./start.sh
```

Скрипт автоматически:
- Проверит наличие Python 3.12
- Создаст виртуальное окружение (если его нет)
- Установит все зависимости
- Инициализирует базу данных
- Применит миграции Alembic
- Запустит сервер

## Требования

- Python 3.12 или выше
- pip (установится автоматически, если отсутствует)
- Доступ к интернету для установки зависимостей

## Особенности для ARM архитектуры (armv7)

Скрипт автоматически определяет ARM архитектуру и использует оптимизированную установку:
- Предпочитает бинарные пакеты (`PIP_PREFER_BINARY=1`)
- Использует `--no-build-isolation` для избежания проблем с сборкой

Если возникают проблемы с установкой `psycopg2-binary` на armv7, установите dev-пакеты:

**Debian/Ubuntu:**
```bash
sudo apt update
sudo apt install python3-dev build-essential libpq-dev
```

**RHEL/CentOS/Rocky:**
```bash
sudo dnf install python3-devel gcc postgresql-devel
```

**Alpine:**
```bash
sudo apk add python3-dev gcc musl-dev postgresql-dev
```

## Ручная установка (если скрипт не работает)

```bash
# 1. Создать виртуальное окружение
python3.12 -m venv venv

# 2. Активировать
source venv/bin/activate

# 3. Обновить pip
python -m pip install --upgrade pip setuptools wheel

# 4. Установить зависимости
# Для armv7:
export PIP_PREFER_BINARY=1
python -m pip install --no-build-isolation -r requirements.txt

# Для других архитектур:
python -m pip install -r requirements.txt

# 5. Инициализировать БД
python init_db.py

# 6. Применить миграции
alembic upgrade head

# 7. Запустить
python run.py
```

## Конфигурация

Перед первым запуском отредактируйте файл `.env` (создается из `env.example`):
- `JWT_SECRET_KEY` - секретный ключ для JWT токенов
- `ADMIN_PASSWORD` - пароль администратора
- `DEBUG` - режим отладки (True/False)
- `WORKERS` - количество воркеров uvicorn

## Доступ к приложению

После запуска приложение будет доступно:
- Локально: http://localhost:8000
- Извне: http://ваш-ip:8000
- API документация: http://localhost:8000/docs

## Остановка сервера

Нажмите `Ctrl+C` в терминале, где запущен сервер.

## Запуск в фоне (systemd)

Создайте файл `/etc/systemd/system/ibolid-cloud.service`:

```ini
[Unit]
Description=IBolid Cloud Application
After=network.target

[Service]
Type=simple
User=ваш-пользователь
WorkingDirectory=/путь/к/проекту
Environment="PATH=/путь/к/проекту/venv/bin"
ExecStart=/путь/к/проекту/venv/bin/python /путь/к/проекту/run.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Затем:
```bash
sudo systemctl daemon-reload
sudo systemctl enable ibolid-cloud
sudo systemctl start ibolid-cloud
sudo systemctl status ibolid-cloud
```

## Логи

Логи приложения можно посмотреть:
```bash
# Если запущен через systemd
sudo journalctl -u ibolid-cloud -f

# Если запущен вручную - логи в консоли
```



