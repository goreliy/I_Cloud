# Инструкция по установке

## Требования

- Python 3.8 или выше
- pip (менеджер пакетов Python)
- PostgreSQL или SQLite (для базы данных)

## Шаги установки

### 1. Клонирование репозитория

```bash
git clone <your-repository-url>
cd cloudtest
```

### 2. Создание виртуального окружения

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**Linux/Mac:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 4. Настройка конфигурации

Скопируйте файл `env.example` в `.env`:

```bash
# Windows
copy env.example .env

# Linux/Mac
cp env.example .env
```

Отредактируйте `.env` файл:

#### Для SQLite (простая настройка):
```env
DATABASE_TYPE=sqlite
DATABASE_URL=sqlite:///./thingspeak.db
```

#### Для PostgreSQL:
```env
DATABASE_TYPE=postgresql
DATABASE_URL=postgresql://username:password@localhost/thingspeak
```

#### Настройка аутентификации:
```env
# Включить аутентификацию
AUTH_ENABLED=true

# Или отключить (открытый доступ)
AUTH_ENABLED=false
```

### 5. Инициализация базы данных

```bash
python init_db.py
```

Эта команда:
- Создаст все необходимые таблицы
- Создаст администратора (если AUTH_ENABLED=true)
- Выведет учетные данные администратора

### 6. (Опционально) Создание тестовых данных

```bash
python create_sample_data.py
```

Создаст:
- Тестового пользователя (test@example.com / test123)
- 3 примера каналов с данными за последние 7 дней

### 7. Запуск приложения

```bash
python run.py
```

Или используя uvicorn напрямую:

```bash
uvicorn app.main:app --reload
```

Приложение будет доступно по адресу:
- **Главная страница**: http://localhost:8000
- **API документация**: http://localhost:8000/docs
- **Alternative API docs**: http://localhost:8000/redoc

## Первый вход

### Если аутентификация включена (AUTH_ENABLED=true):

1. Откройте http://localhost:8000
2. Нажмите "Войти"
3. Используйте учетные данные администратора из `.env` файла:
   - Email: `admin@example.com` (или ваш ADMIN_EMAIL)
   - Password: `admin123` (или ваш ADMIN_PASSWORD)

### Если аутентификация отключена (AUTH_ENABLED=false):

Просто откройте http://localhost:8000 и начните создавать каналы!

## Быстрый тест API

### Создать канал (без аутентификации):

```bash
curl -X POST "http://localhost:8000/api/channels" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Channel",
    "description": "My first IoT channel",
    "public": true,
    "timezone": "UTC"
  }'
```

### Отправить данные:

```bash
# Получите Write API Key из веб-интерфейса
curl "http://localhost:8000/update?api_key=YOUR_WRITE_KEY&field1=25.5&field2=60.2"
```

### Получить данные:

```bash
curl "http://localhost:8000/channels/1/feeds.json?results=10"
```

## Использование PostgreSQL

### 1. Установите PostgreSQL

**Windows:**
Скачайте и установите с https://www.postgresql.org/download/windows/

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
```

**Mac:**
```bash
brew install postgresql
```

### 2. Создайте базу данных

```bash
# Войдите в PostgreSQL
sudo -u postgres psql

# Создайте базу данных и пользователя
CREATE DATABASE thingspeak;
CREATE USER thingspeak_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE thingspeak TO thingspeak_user;
\q
```

### 3. Обновите .env

```env
DATABASE_TYPE=postgresql
DATABASE_URL=postgresql://thingspeak_user:your_password@localhost/thingspeak
```

### 4. Запустите инициализацию

```bash
python init_db.py
```

## Решение проблем

### Ошибка при установке psycopg2-binary

Если возникают проблемы с установкой PostgreSQL драйвера:

**Windows:**
Установите Visual C++ Build Tools

**Linux:**
```bash
sudo apt install python3-dev libpq-dev
```

**Mac:**
```bash
brew install postgresql
```

Затем повторите:
```bash
pip install psycopg2-binary
```

### Ошибка "ModuleNotFoundError"

Убедитесь, что виртуальное окружение активировано:
```bash
# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### База данных не создается

Проверьте права доступа к файлу/директории для SQLite или учетные данные для PostgreSQL.

## Производственное развертывание

Для production использования:

1. Измените секретные ключи в `.env`:
```env
JWT_SECRET_KEY=<генерируйте случайный ключ>
ADMIN_PASSWORD=<надежный пароль>
```

2. Отключите debug режим:
```env
DEBUG=false
```

3. Используйте PostgreSQL вместо SQLite

4. Используйте production WSGI сервер:
```bash
pip install gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

5. Настройте NGINX как reverse proxy

6. Используйте HTTPS сертификаты (Let's Encrypt)

## Дополнительная информация

- **Документация API**: http://localhost:8000/docs
- **GitHub**: <your-repo-url>
- **Лицензия**: MIT

