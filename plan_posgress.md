<!-- 3f3b9dee-37d6-4564-90a2-0ffd52b11d8f 570edb36-b833-48a3-bc35-512857932ea0 -->
# План: админская настройка бэкенда архива (SQLite/PostgreSQL)

## 1) Требования и допущения
- По умолчанию архив работает на локальном SQLite-файле (например, `archive/archive.db`).
- В админке доступны:
  - выбор бэкенда: SQLite (с выбором файла) или PostgreSQL (набор полей подключения),
  - параметры: период удержания данных (ретеншн), расписание запуска, режим «копировать и удалять из основной БД»,
  - кнопки: «Проверить подключение», «Сохранить», «Запустить архивирование сейчас», отображение статуса/логов.
- Архивируются в первую очередь `feeds` (+ опционально `request_log` позже).

## 2) Конфигурация и модели
- Файл: `app/models/archive_config.py`
  - Таблица `archive_settings`: `id(1)`, `enabled`, `backend_type` (enum: `sqlite|postgres`),
    - Для SQLite: `sqlite_file_path` (строка),
    - Для Postgres: `pg_host`, `pg_port`, `pg_db`, `pg_user`, `pg_password`, `pg_schema` (опц), `pg_ssl` (bool),
    - Общие: `retention_days` (int), `schedule_cron` (строка или `interval_sec`), `copy_then_delete` (bool),
    - Тех.: `last_run_at`, `last_status`, `last_error`.
- Pydantic-схемы: `app/schemas/archive.py` (get/update, test connection, run now, status).
- Alembic-миграция: `alembic/versions/009_archive_settings.py` (создание таблицы + enum).
- Bootstrap: при старте, если записи нет — создать дефолт с `backend_type=sqlite, sqlite_file_path="archive/archive.db", retention_days=30, enabled=false`.

## 3) Бэкенды и сервис архива
- Интерфейс: `app/services/archive/backends.py`
  - `class ArchiveBackend`: `test_connection()`, `init_schema()`, `archive_batch(since_before, batch_size)`, `finalize_run()`.
  - Реализации:
    - `SQLiteArchiveBackend`: отдельный SQLAlchemy engine на выбранный файл, проверка наличия директорий, auto-`init_schema()`.
    - `PostgresArchiveBackend`: engine по собранному DSN, поддержка ssl (при необходимости), `init_schema()`.
- Сервис: `app/services/archive_service.py`
  - `load_config(db)`, `get_backend(config)`,
  - `archive_once(cutoff_dt, batch_size=1000, copy_then_delete=True)`: копирование в таблицы архива (`feeds_archive`), затем удаление из основной БД по `created_at < cutoff_dt` при включённой опции,
  - ведение статистики: перемещено N, длительность, ошибки.
- Планировщик: `app/services/archive_scheduler.py`
  - Запуск фоновой задачи на старте приложения (respect `enabled`), по `schedule_cron` или `interval_sec`.
  - Возможность безопасной остановки на shutdown.

## 4) Админский UI и роуты
- Страница: `GET /admin/archive` → `app/templates/admin/archive.html`.
  - 
    - Переключатель бэкенда (радио): SQLite / PostgreSQL.
    - Для SQLite: поле пути к файлу + кнопка «создать директорию/файл при сохранении».
    - Для PostgreSQL: host, port, db, user, password (masked), schema (опц), ssl (checkbox).
    - Общие: retention_days, расписание (крон-строка или число секунд), флаг copy_then_delete.
    - Кнопки: «Проверить подключение», «Сохранить», «Запустить сейчас», «Остановить/Запустить планировщик».
    - Блок «Статус»: last_run_at, last_status, последний лог/ошибка, счётчики.
- API (новый модуль): `app/routers/admin_archive.py` (admin-only)
  - `GET /api/admin/archive/config` — получить конфиг,
  - `PUT /api/admin/archive/config` — сохранить конфиг (и перезапустить планировщик),
  - `POST /api/admin/archive/test` — тест подключения/инициализации схемы,
  - `POST /api/admin/archive/run` — ручной запуск `archive_once`,
  - `GET /api/admin/archive/status` — текущий статус/последний результат.
- В `app/main.py` подключить роутер, шаблон — через `web.py` → `/admin/archive`.

## 5) Поведение по умолчанию и переключение
- По умолчанию: SQLite (локальный файл), планировщик выключен (`enabled=false`), retention=30.
- При включении PostgreSQL:
  - сначала «Проверить подключение», затем «Сохранить», затем «Инициализировать схему архива» (выполняется автоматически при первом запуске).
- Переключение бэкенда:
  - Остановить планировщик → проверить новый бэкенд → сохранить конфиг → перезапустить планировщик.
  - (Опция) «Перенести уже архивированные данные» — отдельная кнопка/процедура (можно отложить).

## 6) Безопасность и валидации
- Доступ только администратору.
- Пароль PostgreSQL хранить в БД зашифрованным (минимально — base64 + соль; лучше — Fernet с `settings.SECRET_KEY`).
- Белый список директорий для sqlite (например, `./archive`), предупреждение при выходе за пределы.
- Ограничение частоты ручного запуска.

## 7) Наблюдаемость
- Логи архивации: успех/ошибка, количество перемещённых записей, длительность, batch-статистика.
- Публичный статус в админке: прогресс текущего запуска, последний результат.

## 8) Миграции и схемы архива
- В `init_schema()` создавать таблицы `feeds_archive` идентичные `feeds` (+ индексы по `channel_id`, `created_at`).
- При необходимости — компактные индексы и vacuum/analyze.

## 9) Тестирование и документация
- Юнит-тесты: выбор бэкенда, тест подключения, dry-run архивации на фикстурах SQLite.
- Интеграционные: ручной запуск на тестовом канале с данными, проверка удаления при `copy_then_delete`.
- Документация: раздел «Архивация данных» — настройка, расписание, миграции с/на PostgreSQL, рекомендации по производительности.


### To-dos

- [ ] Добавить модели и миграцию для archive_settings и enum backend_type
- [ ] Реализовать ArchiveBackend (SQLite/Postgres), init_schema, archive_once, test_connection
- [ ] Добавить планировщик фонового запуска архивации и управление старт/стоп
- [ ] Создать страницу /admin/archive с формой выбора бэкенда и параметров
- [ ] Добавить API: get/put config, test, run, status (admin-only)
- [ ] Валидации, шифрование пароля, тесты, документация

