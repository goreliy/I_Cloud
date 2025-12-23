# Описание модулей Backend

## Общая структура

Backend система построена по модульной архитектуре с четким разделением ответственности:

```
app/
├── models/          # Модели данных (SQLAlchemy)
├── schemas/         # Схемы валидации (Pydantic)
├── routers/        # API endpoints (FastAPI)
├── services/       # Бизнес-логика
├── middleware/     # Middleware компоненты
├── dependencies.py # Зависимости и утилиты
├── config.py       # Конфигурация
├── database.py     # Настройка БД
└── main.py         # Точка входа приложения
```

---

## 1. Модуль моделей данных (`app/models/`)

### 1.1. User (`user.py`)

**Назначение**: Модель пользователя системы.

**Поля:**
- `id` (Integer, PK) — уникальный идентификатор
- `email` (String, unique) — email пользователя
- `hashed_password` (String) — хешированный пароль
- `is_active` (Boolean) — активен ли пользователь
- `is_admin` (Boolean) — является ли администратором
- `last_login` (DateTime) — дата последнего входа
- `created_at` (DateTime) — дата создания

**Связи:**
- `channels` — каналы пользователя (One-to-Many)
- `profile` — профиль пользователя (One-to-One)

---

### 1.2. UserProfile (`user_profile.py`)

**Назначение**: Расширенный профиль пользователя.

**Поля:**
- `id` (Integer, PK)
- `user_id` (Integer, FK) — ссылка на пользователя
- `display_name` (String) — отображаемое имя
- `avatar_url` (String) — URL аватара
- `bio` (Text) — биография
- `website` (String) — сайт
- `location` (String) — местоположение
- `created_at`, `updated_at` (DateTime)

**Связи:**
- `user` — пользователь (Many-to-One)

---

### 1.3. Channel (`channel.py`)

**Назначение**: Модель канала данных.

**Поля:**
- `id` (Integer, PK)
- `user_id` (Integer, FK, nullable) — владелец канала
- `name` (String) — название канала
- `description` (Text) — описание
- `public` (Boolean) — публичный ли канал
- `timezone` (String) — часовой пояс
- `last_entry_id` (Integer) — последний ID записи

**Кастомизация:**
- `image_url` (String) — изображение канала
- `background_url` (String) — фоновое изображение
- `color_scheme` (String) — цветовая схема
- `custom_css` (Text) — кастомный CSS

**Названия и видимость полей:**
- `field1_label` до `field8_label` (String) — названия полей
- `field1_visible` до `field8_visible` (Boolean) — видимость полей

**Связи:**
- `user` — владелец (Many-to-One)
- `feeds` — записи данных (One-to-Many)
- `api_keys` — API ключи (One-to-Many)
- `widgets` — виджеты (One-to-Many)
- `automation_rules` — правила автоматизации (One-to-Many)

---

### 1.4. Feed (`feed.py`)

**Назначение**: Модель записи данных канала.

**Поля:**
- `id` (Integer, PK)
- `channel_id` (Integer, FK) — канал
- `entry_id` (Integer) — порядковый номер записи в канале
- `created_at` (DateTime) — время создания

**Данные:**
- `field1` до `field8` (Float, nullable) — данные полей

**Геолокация:**
- `latitude` (Float) — широта
- `longitude` (Float) — долгота
- `elevation` (Float) — высота

**Статус:**
- `status` (Text) — статусное сообщение

**Связи:**
- `channel` — канал (Many-to-One)

---

### 1.5. ApiKey (`api_key.py`)

**Назначение**: Модель API ключа для доступа к каналу.

**Поля:**
- `id` (Integer, PK)
- `channel_id` (Integer, FK) — канал
- `key` (String, unique) — сам ключ
- `type` (String) — тип: "read" или "write"
- `name` (String) — название ключа
- `is_active` (Boolean) — активен ли ключ
- `created_at` (DateTime)

**Связи:**
- `channel` — канал (Many-to-One)

---

### 1.6. CustomWidget (`custom_widget.py`)

**Назначение**: Модель пользовательского виджета.

**Поля:**
- `id` (Integer, PK)
- `channel_id` (Integer, FK) — канал
- `name` (String) — название виджета
- `widget_type` (String) — тип: "svg" или "html"
- `width` (Integer) — ширина в колонках Bootstrap
- `height` (Integer) — высота в пикселях
- `svg_file_url` (String) — URL SVG файла (для svg виджетов)
- `svg_bindings` (Text, JSON) — привязки данных к SVG элементам
- `html_code` (Text) — HTML код (для html виджетов)
- `css_code` (Text) — CSS код
- `js_code` (Text) — JavaScript код
- `ai_service_id` (Integer, FK) — использованный AI сервис
- `prompt_used` (Text) — использованный промпт
- `created_at`, `updated_at` (DateTime)

**Связи:**
- `channel` — канал (Many-to-One)
- `ai_service` — AI сервис (Many-to-One)
- `versions` — версии виджета (One-to-Many)

---

### 1.7. WidgetVersion (`widget_version.py`)

**Назначение**: Модель версии виджета.

**Поля:**
- `id` (Integer, PK)
- `widget_id` (Integer, FK) — виджет
- `version_number` (Integer) — номер версии
- `comment` (String) — комментарий к версии
- `svg_file_url` (String) — URL SVG файла
- `svg_bindings` (Text, JSON)
- `html_code`, `css_code`, `js_code` (Text)
- `created_at` (DateTime)

**Связи:**
- `widget` — виджет (Many-to-One)

---

### 1.8. AutomationRule (`automation_rule.py`)

**Назначение**: Модель правила автоматизации.

**Поля:**
- `id` (Integer, PK)
- `channel_id` (Integer, FK) — канал
- `name` (String) — название правила
- `rule_type` (String) — тип: "threshold", "pid", "expression"
- `priority` (Integer) — приоритет (меньше = выше)
- `is_active` (Boolean) — активно ли правило

**Для порогового правила:**
- `trigger_field` (String) — поле триггера (field1-8)
- `condition` (String) — условие: ">", "<", ">=", "<=", "==", "!="
- `threshold_value` (Float) — пороговое значение
- `target_field` (String) — целевое поле
- `action_type` (String) — тип действия
- `action_value` (Float) — значение действия

**Для PID контроллера:**
- `pid_setpoint` (Float) — заданное значение
- `pid_kp`, `pid_ki`, `pid_kd` (Float) — коэффициенты
- `pid_output_min`, `pid_output_max` (Float) — границы выхода

**Для выражения:**
- `expression` (String) — выражение для вычисления

**Связи:**
- `channel` — канал (Many-to-One)

---

### 1.9. AIService (`ai_service.py`)

**Назначение**: Модель AI сервиса для генерации виджетов.

**Поля:**
- `id` (Integer, PK)
- `alias` (String, unique) — алиас сервиса
- `name` (String) — название
- `provider` (String) — провайдер (openai, anthropic и т.д.)
- `api_key_enc` (String) — зашифрованный API ключ
- `model` (String) — модель AI
- `base_url` (String) — базовый URL API
- `scope` (String) — область действия: "global", "user", "channel"
- `is_active` (Boolean)
- `created_at`, `updated_at` (DateTime)

**Связи:**
- `widgets` — виджеты (One-to-Many)
- `prompt_overrides` — переопределения промптов (One-to-Many)

---

### 1.10. RequestLog (`request_log.py`)

**Назначение**: Модель лога API запроса.

**Поля:**
- `id` (Integer, PK)
- `method` (String) — HTTP метод
- `url` (String) — URL запроса
- `status_code` (Integer) — код ответа
- `response_time` (Float) — время ответа в мс
- `ip_address` (String) — IP адрес
- `user_agent` (String) — User-Agent
- `timestamp` (DateTime) — время запроса

---

### 1.11. ArchiveSettings (`archive_config.py`)

**Назначение**: Модель настроек архивации данных.

**Поля:**
- `id` (Integer, PK)
- `enabled` (Boolean) — включена ли архивация
- `backend_type` (String) — тип backend: "sqlite" или "postgresql"
- `sqlite_file_path` (String) — путь к SQLite файлу
- `pg_host`, `pg_port`, `pg_db`, `pg_user` (String) — параметры PostgreSQL
- `pg_password_enc` (String) — зашифрованный пароль
- `pg_schema` (String) — схема БД
- `pg_ssl` (Boolean) — использовать SSL
- `retention_days` (Integer) — период хранения в днях
- `schedule_interval_seconds` (Integer) — интервал архивации
- `copy_then_delete` (Boolean) — стратегия архивации
- `last_run_at` (DateTime) — время последнего запуска
- `created_at`, `updated_at` (DateTime)

---

### 1.12. StressTestRun (`stress_test.py`)

**Назначение**: Модель запуска стресс-теста.

**Поля:**
- `id` (Integer, PK)
- `url` (String) — тестируемый URL
- `method` (String) — HTTP метод
- `workers` (Integer) — количество воркеров
- `rps` (Integer) — запросов в секунду
- `duration_seconds` (Integer) — длительность теста
- `status` (String) — статус: "running", "completed", "failed"
- `results_json` (Text, JSON) — результаты теста
- `started_at`, `completed_at` (DateTime)

---

## 2. Модуль схем валидации (`app/schemas/`)

Схемы Pydantic используются для валидации входных и выходных данных API.

### Основные схемы:
- `UserCreate`, `UserLogin`, `UserResponse` — пользователи
- `ChannelCreate`, `ChannelUpdate`, `ChannelResponse` — каналы
- `FeedCreate`, `FeedResponse` — записи данных
- `ApiKeyCreate`, `ApiKeyResponse` — API ключи
- `CustomWidgetResponse`, `CustomWidgetUpdate` — виджеты
- `AutomationRuleCreate`, `AutomationRuleUpdate`, `AutomationRuleResponse` — автоматизация
- `AIServiceCreate`, `AIServiceUpdate`, `AIServiceResponse` — AI сервисы

---

## 3. Модуль роутеров (`app/routers/`)

### 3.1. auth.py
**Endpoints:**
- `POST /api/auth/register` — регистрация
- `POST /api/auth/login` — вход
- `GET /api/auth/me` — текущий пользователь

### 3.2. channels.py
**Endpoints:**
- `POST /api/channels` — создание канала
- `GET /api/channels` — список каналов
- `GET /api/channels/{id}` — информация о канале
- `PUT /api/channels/{id}` — обновление канала
- `DELETE /api/channels/{id}` — удаление канала
- `POST /api/channels/{id}/api-keys` — создание API ключа
- `GET /api/channels/{id}/api-keys` — список ключей
- `DELETE /api/channels/{id}/api-keys/{key_id}` — удаление ключа

### 3.3. feeds.py
**Endpoints:**
- `POST /update` — запись данных (ThingSpeak совместимый)
- `GET /update` — запись данных (GET метод)
- `GET /channels/{id}/feeds.json` — получение данных (JSON)
- `GET /channels/{id}/feeds.csv` — экспорт в CSV
- `GET /channels/{id}/feeds.xml` — экспорт в XML

### 3.4. widgets.py
**Endpoints:**
- `POST /api/channels/{id}/widgets` — создание виджета
- `GET /api/channels/{id}/widgets` — список виджетов
- `GET /api/channels/{id}/widgets/{widget_id}` — информация о виджете
- `PUT /api/channels/{id}/widgets/{widget_id}` — обновление виджета
- `DELETE /api/channels/{id}/widgets/{widget_id}` — удаление виджета
- `GET /api/channels/{id}/widgets/{widget_id}/versions` — версии виджета

### 3.5. automation.py
**Endpoints:**
- `POST /api/channels/{id}/automation` — создание правила
- `GET /api/channels/{id}/automation` — список правил
- `PUT /api/channels/{id}/automation/{rule_id}` — обновление правила
- `DELETE /api/channels/{id}/automation/{rule_id}` — удаление правила

### 3.6. admin.py
**Endpoints:**
- `GET /api/admin/stats` — статистика системы
- `GET /api/admin/users` — список пользователей
- `GET /api/admin/channels` — список каналов
- `GET /api/admin/requests` — логи запросов
- `PUT /api/admin/users/{id}` — обновление пользователя
- `DELETE /api/admin/users/{id}` — удаление пользователя

### 3.7. admin_archive.py
**Endpoints:**
- `GET /api/admin/archive/config` — конфигурация архивации
- `PUT /api/admin/archive/config` — обновление конфигурации
- `POST /api/admin/archive/run-now` — запуск архивации

### 3.8. web.py
**Endpoints:** Веб-страницы (HTML):
- `GET /` — главная страница
- `GET /channels` — список каналов
- `GET /channels/create` — создание канала
- `GET /channels/{id}` — детали канала
- `GET /channels/{id}/edit` — редактирование канала
- `GET /channels/{id}/settings` — настройки канала
- `GET /channels/{id}/widgets` — виджеты канала
- `GET /channels/{id}/automation` — автоматизация
- `GET /login` — страница входа
- `GET /register` — страница регистрации
- `GET /settings` — настройки пользователя
- `GET /admin` — админ-панель

### 3.9. control.py
**Endpoints:**
- `POST /api/control/widget/{widget_id}/execute` — выполнение кода виджета

### 3.10. stress_test.py
**Endpoints:**
- `POST /api/stress-test/run` — запуск стресс-теста
- `GET /api/stress-test/results/{test_id}` — результаты теста

---

## 4. Модуль сервисов (`app/services/`)

### 4.1. channel_service.py
**Функции:**
- `create_channel()` — создание канала
- `get_channel()` — получение канала по ID
- `get_channels()` — список каналов с фильтрацией
- `update_channel()` — обновление канала
- `delete_channel()` — удаление канала
- `check_channel_access()` — проверка доступа к каналу
- `generate_api_key()` — генерация API ключа

### 4.2. feed_service.py
**Функции:**
- `create_feed()` — создание записи данных
- `get_feeds()` — получение записей с фильтрацией
- `get_last_feed()` — последняя запись канала
- `get_field_data()` — данные конкретного поля

### 4.3. data_processor.py
**Функции:**
- `aggregate_feeds()` — агрегация данных (average, sum, median, min, max)
- `process_feeds()` — обработка данных для экспорта

### 4.4. auth_service.py
**Функции:**
- `create_user()` — создание пользователя
- `authenticate_user()` — аутентификация
- `create_access_token()` — создание JWT токена
- `get_or_create_admin()` — создание администратора

### 4.5. upload_service.py
**Функции:**
- `upload_channel_image()` — загрузка изображения канала
- `upload_channel_background()` — загрузка фона канала
- `upload_avatar()` — загрузка аватара пользователя
- `upload_svg_widget()` — загрузка SVG виджета
- `resize_image()` — изменение размера изображения

### 4.6. widget_version_service.py
**Функции:**
- `create_version()` — создание версии виджета
- `get_versions()` — список версий виджета
- `restore_version()` — восстановление версии

### 4.7. ai_widget_service.py
**Функции:**
- `generate_widget()` — генерация виджета через AI
- `refine_prompt()` — улучшение промпта
- `call_ai_service()` — вызов AI API

### 4.8. automation_service.py
**Функции:**
- `process_automation_rules()` — обработка правил автоматизации
- `evaluate_threshold_rule()` — оценка порогового правила
- `evaluate_pid_controller()` — оценка PID контроллера
- `evaluate_expression()` — оценка выражения

### 4.9. channel_stats.py
**Функции:**
- `get_channel_statistics()` — статистика канала
- `get_field_statistics()` — статистика поля

### 4.10. mem_buffer.py
**Класс:** `MemBuffer`
**Назначение:** In-memory буфер для оптимизации записи данных.

**Параметры:**
- `max_queue` — максимум записей в очереди (50000)
- `batch_size` — размер батча (200)
- `flush_interval_ms` — интервал сброса (100ms)
- `max_latency_ms` — максимальная задержка (500ms)

**Методы:**
- `add()` — добавление записи в буфер
- `start()` — запуск буфера
- `drain_and_stop()` — сброс и остановка

### 4.11. archive/
**Подмодуль архивации данных:**

#### service.py
- `load_config()` — загрузка конфигурации
- `apply_update()` — обновление конфигурации
- `run_archive()` — выполнение архивации

#### scheduler.py
- `ArchiveScheduler` — планировщик архивации
- `start()` — запуск планировщика
- `stop()` — остановка планировщика

#### backends.py
- `ArchiveBackend` — базовый класс backend
- `SQLiteArchiveBackend` — реализация для SQLite
- `PostgresArchiveBackend` — реализация для PostgreSQL

#### migration.py
- `migrate_data()` — миграция данных в архив

---

## 5. Модуль middleware (`app/middleware/`)

### 5.1. logging_middleware.py
**Класс:** `RequestLoggingMiddleware`
**Назначение:** Логирование всех API запросов.

**Логирует:**
- HTTP метод
- URL
- Код ответа
- Время ответа
- IP адрес
- User-Agent

### 5.2. rate_limiter.py
**Класс:** `RateLimitMiddleware`
**Назначение:** Ограничение частоты запросов.

**Параметры:**
- Лимит: 100 запросов в минуту на IP
- Работает только в production режиме

### 5.3. root_path_middleware.py
**Класс:** `RootPathMiddleware`
**Назначение:** Поддержка работы за реверс-прокси.

**Функционал:**
- Добавление префикса `ROOT_PATH` к путям
- Корректная обработка URL за прокси

---

## 6. Модуль зависимостей (`app/dependencies.py`)

**Функции:**
- `get_current_user()` — получение текущего пользователя (требует аутентификации)
- `get_current_user_optional()` — получение текущего пользователя (опционально)
- `get_current_admin()` — получение администратора
- `verify_api_key()` — проверка API ключа

---

## 7. Модуль конфигурации (`app/config.py`)

**Класс:** `Settings` (Pydantic BaseSettings)

**Параметры:**
- `DATABASE_TYPE` — тип БД (sqlite/postgresql)
- `DATABASE_URL` — URL подключения
- `AUTH_ENABLED` — включение аутентификации
- `JWT_SECRET_KEY` — секретный ключ JWT
- `JWT_ALGORITHM` — алгоритм JWT
- `ACCESS_TOKEN_EXPIRE_MINUTES` — время жизни токена
- `MEMBUFFER_ENABLED` — включение буфера записи
- `MEMBUFFER_MAX_QUEUE` — максимум записей в очереди
- `MEMBUFFER_BATCH_SIZE` — размер батча
- `MEMBUFFER_FLUSH_INTERVAL_MS` — интервал сброса
- `ROOT_PATH` — префикс пути для реверс-прокси
- И другие параметры производительности и безопасности

---

## 8. Модуль базы данных (`app/database.py`)

**Компоненты:**
- `engine` — SQLAlchemy engine
- `SessionLocal` — фабрика сессий
- `Base` — базовый класс для моделей
- `get_db()` — dependency для получения сессии БД

**Особенности:**
- Поддержка SQLite и PostgreSQL
- Настройка пула соединений
- Оптимизация SQLite (WAL режим)
- Автоматическое создание таблиц

---

## Взаимодействие модулей

```
Request → Middleware → Router → Dependency → Service → Model → Database
                                    ↓
                                 Schema (Validation)
                                    ↓
                                 Response
```

1. **Request** поступает в приложение
2. **Middleware** обрабатывает запрос (логирование, rate limiting)
3. **Router** определяет endpoint и вызывает handler
4. **Dependency** проверяет аутентификацию и получает данные
5. **Schema** валидирует входные данные
6. **Service** выполняет бизнес-логику
7. **Model** взаимодействует с БД
8. **Response** возвращается клиенту

---

## Расширяемость

Система легко расширяется:
- Добавление новых моделей в `models/`
- Создание новых схем в `schemas/`
- Добавление endpoints в `routers/`
- Реализация бизнес-логики в `services/`
- Добавление middleware в `middleware/`

Все компоненты слабо связаны и могут быть легко заменены или расширены.

