# IBolid Cloud — Документация

Этот файл — единая точка входа в документацию проекта. Здесь собраны ссылки на все разделы и краткие инструкции.

## Быстрый старт
- Установка, запуск, конфигурация: см. корневой `README.md` (актуальный)
- Важно: `.env` → `DEBUG=false`, `WORKERS=4` для продакшена

## Администрирование
- Админ‑панель: `/admin`
- Мониторинг:
  - CPU/RAM/Disk (системные)
  - Память приложения (Process RSS + Children) — раздел Dashboard
  - Буфер записи (In‑Memory) — `/api/admin/membuffer/stats`
- Очистка буфера: `POST /api/admin/membuffer/flush`

## Запись/Чтение данных
- Запись: `/update?api_key=...&field1=...`
- Чтение: `/channels/{id}/feeds.json|csv|xml`
- Экспорт: JSON/XML/CSV

## Производительность
- In‑Memory буфер записи (write‑back): включён через `MEMBUFFER_ENABLED=true`
- Параметры буфера: `MEMBUFFER_BATCH_SIZE`, `MEMBUFFER_FLUSH_INTERVAL_MS`
- SQLite тюнинг: WAL, synchronous=NORMAL (по умолчанию включено)
- Пул соединений: `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `DB_POOL_TIMEOUT`

## Нагрузочное тестирование
- Скрипт: `tests/stress_test.py` (RPS/Workers/Duration)
- Быстрые .bat сценарии: `стресс_тест_*.bat`
- Советы:
  - Временно повысить лимит RateLimiter в `app/middleware/rate_limiter.py`
  - Следить за пулом БД и памятью приложения

## Импорт/Экспорт (план)
- Импорт каналов и данных из JSON/URL (совместимый с ThingSpeak) — отдельный план внедрения

## Troubleshooting
- Ошибка пула соединений: увеличьте `DB_POOL_SIZE/DB_MAX_OVERFLOW`, включите буфер
- 429 от лимитера: увеличьте лимиты или отключите на время тестов
- “Too many file descriptors”: уменьшите `timeout_keep_alive`, добавьте `limit_concurrency`, используйте Linux

## Архивная документация
- См. `docs/ARCHIVE_INDEX.md` — список всех исторических .md файлов с краткими описаниями
