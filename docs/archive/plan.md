# План реализации ThingSpeak на FastAPI

## Архитектура проекта

Приложение будет состоять из следующих компонентов:
- **Backend API** (FastAPI) - RESTful API для работы с данными
- **Frontend** (HTML/JS с Jinja2 templates) - веб-интерфейс для управления и визуализации
- **База данных** - PostgreSQL/SQLite с поддержкой миграций (Alembic)
- **Система аутентификации** - JWT + API ключи с возможностью отключения
- **Графики** - Chart.js или Plotly для визуализации данных

## Основной функционал

### 1. Базовая структура проекта
```
cloudtest/
├── app/
│   ├── __init__.py
│   ├── main.py                 # Точка входа FastAPI
│   ├── config.py              # Конфигурация (БД, auth режим)
│   ├── database.py            # Настройка БД и сессий
│   ├── dependencies.py        # Зависимости для роутов
│   ├── models/                # SQLAlchemy модели
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── channel.py
│   │   ├── feed.py
│   │   └── api_key.py
│   ├── schemas/               # Pydantic схемы
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── channel.py
│   │   ├── feed.py
│   │   └── api_key.py
│   ├── routers/               # API endpoints
│   │   ├── __init__.py
│   │   ├── auth.py           # Регистрация/логин
│   │   ├── channels.py       # CRUD каналов
│   │   ├── feeds.py          # Запись/чтение данных
│   │   ├── admin.py          # Админ панель
│   │   └── web.py            # Веб интерфейс
│   ├── services/              # Бизнес-логика
│   │   ├── __init__.py
│   │   ├── auth_service.py
│   │   ├── channel_service.py
│   │   ├── feed_service.py
│   │   └── data_processor.py # Обработка данных
│   ├── templates/             # Jinja2 шаблоны
│   │   ├── base.html
│   │   ├── index.html
│   │   ├── channels.html
│   │   ├── channel_detail.html
│   │   └── admin/
│   └── static/                # CSS/JS/изображения
│       ├── css/
│       ├── js/
│       └── img/
├── alembic/                   # Миграции БД
├── tests/                     # Тесты
├── .env.example               # Пример конфигурации
├── requirements.txt
└── README.md
```

### 2. Модели данных (SQLAlchemy)

**User** (пользователи):
- id, email, hashed_password, created_at, is_active, is_admin

**Channel** (каналы):
- id, user_id, name, description, public (bool), timezone, created_at, updated_at
- last_entry_id (счетчик записей)

**Feed** (данные каналов):
- id, channel_id, created_at, entry_id
- field1-field8 (Float, nullable) - 8 полей данных
- latitude, longitude, elevation (Float, nullable)
- status (Text, nullable)

**ApiKey** (API ключи):
- id, channel_id, key, type (read/write), created_at, is_active

### 3. API Endpoints

#### Аутентификация (если включена)
- `POST /api/auth/register` - регистрация
- `POST /api/auth/login` - получение JWT токена
- `GET /api/auth/me` - информация о текущем пользователе

#### Каналы
- `POST /api/channels` - создание канала
- `GET /api/channels` - список каналов пользователя
- `GET /api/channels/{id}` - детали канала
- `PUT /api/channels/{id}` - обновление канала
- `DELETE /api/channels/{id}` - удаление канала
- `POST /api/channels/{id}/api-keys` - генерация API ключа
- `GET /api/channels/{id}/api-keys` - список ключей

#### Запись данных (ThingSpeak API совместимость)
- `POST /update` - запись данных (query params или JSON)
- `GET /update?api_key={key}&field1={val}...` - запись через GET

#### Чтение данных
- `GET /channels/{id}/feeds.json` - все записи (JSON)
- `GET /channels/{id}/feeds.xml` - все записи (XML)
- `GET /channels/{id}/feeds.csv` - все записи (CSV)
- `GET /channels/{id}/feeds/last.json` - последняя запись
- `GET /channels/{id}/field/{n}.json` - данные одного поля

#### Параметры чтения
- `results={n}` - количество записей (по умолчанию 100)
- `start={datetime}` - начало периода
- `end={datetime}` - конец периода
- `timescale={minutes}` - агрегация по времени
- `average={minutes}` - среднее значение
- `median={minutes}` - медиана
- `sum={minutes}` - сумма
- `round={n}` - округление

#### Веб интерфейс
- `GET /` - главная страница
- `GET /channels` - список каналов
- `GET /channels/{id}` - просмотр канала с графиками
- `GET /channels/{id}/edit` - редактирование канала
- `GET /admin` - админ панель (если авторизован)

### 4. Конфигурация (.env)

```env
# Database
DATABASE_TYPE=postgresql  # postgresql / sqlite
DATABASE_URL=postgresql://user:pass@localhost/thingspeak
# или DATABASE_URL=sqlite:///./thingspeak.db

# Authentication
AUTH_ENABLED=true  # true / false
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Application
APP_NAME=ThingSpeak FastAPI
DEBUG=false
CORS_ORIGINS=["http://localhost:3000"]

# Admin (при первом запуске)
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=admin123
```

### 5. Обработка данных (data_processor.py)

Реализовать функции:
- `timescale_data(feeds, minutes)` - агрегация по времени
- `calculate_average(feeds, minutes)` - вычисление среднего
- `calculate_median(feeds, minutes)` - вычисление медианы
- `calculate_sum(feeds, minutes)` - вычисление суммы
- `round_values(feeds, decimals)` - округление значений

### 6. Система аутентификации

**Режим с аутентификацией (AUTH_ENABLED=true)**:
- JWT токены для веб-интерфейса
- API ключи для записи/чтения данных
- Middleware для проверки прав доступа
- Пользователь может видеть только свои каналы

**Режим без аутентификации (AUTH_ENABLED=false)**:
- Все endpoints доступны без токенов
- API ключи не проверяются (но можно указывать)
- Все каналы видны всем
- Упрощенный веб-интерфейс

### 7. Веб интерфейс

**Главная страница**:
- Информация о сервисе
- Кнопки регистрации/входа (если AUTH_ENABLED)
- Список публичных каналов

**Страница канала**:
- Информация о канале
- Графики для каждого поля (Chart.js/Plotly)
- Таблица последних записей
- Экспорт данных (JSON/XML/CSV)
- Настройки отображения (период, агрегация)

**Админ панель** (если пользователь админ):
- Статистика системы
- Управление пользователями
- Управление каналами
- Просмотр логов

### 8. Графики и визуализация

Использовать Chart.js для отрисовки:
- Line charts для временных рядов
- Возможность выбора полей для отображения
- Zoom/pan функционал
- Экспорт графиков в PNG
- Real-time обновление (опционально, через WebSocket)

### 9. Зависимости (requirements.txt)

```
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
alembic==1.12.1
psycopg2-binary==2.9.9
aiosqlite==0.19.0
pydantic==2.5.0
pydantic-settings==2.1.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
jinja2==3.1.2
python-dotenv==1.0.0
```

### 10. Миграции базы данных

Использовать Alembic для управления схемой БД:
- Инициализация: `alembic init alembic`
- Создание миграций: `alembic revision --autogenerate -m "message"`
- Применение: `alembic upgrade head`

### 11. Тестирование

Покрыть тестами:
- API endpoints (pytest + httpx)
- Обработка данных (unit tests)
- Аутентификация и авторизация
- Различные режимы конфигурации

## Порядок реализации

1. Настройка структуры проекта и конфигурации
2. Модели данных и миграции БД
3. Базовые CRUD операции для каналов
4. Система аутентификации (с возможностью отключения)
5. API для записи данных (ThingSpeak compatible)
6. API для чтения данных с форматами JSON/XML/CSV
7. Обработка данных (агрегация, статистика)
8. Веб-интерфейс (базовые страницы)
9. Графики и визуализация
10. Админ панель
11. Тестирование и документация

