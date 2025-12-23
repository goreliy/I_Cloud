# Инструкция по применению изменений на сервере

## Шаг 1: Копирование файлов

Скопируйте все измененные файлы на сервер в директорию проекта (например, `/opt/cloudtest` или `/home/gorelyi/CloudTest`).

## Шаг 2: Применение миграций базы данных

### Вариант A: Через Alembic (рекомендуется)

```bash
# Активируйте виртуальное окружение
cd /opt/cloudtest  # или ваш путь к проекту
source venv/bin/activate  # или . venv/bin/activate

# Примените миграции
alembic upgrade head
```

### Вариант B: Если Alembic не работает

Можно применить миграцию вручную через SQL:

```bash
# Для SQLite
sqlite3 ibolid.db < migration_011.sql

# Для PostgreSQL
psql -U your_user -d your_database -f migration_011.sql
```

Или выполните SQL команды вручную (см. файл `alembic/versions/011_add_plans.py`).

## Шаг 3: Перезапуск приложения

### Если используется systemd сервис:

```bash
# Остановить сервис
sudo systemctl stop myapp.service

# Проверить статус
sudo systemctl status myapp.service

# Запустить сервис
sudo systemctl start myapp.service

# Или перезапустить сразу
sudo systemctl restart myapp.service

# Просмотр логов
sudo journalctl -u myapp.service -f
```

### Если запускается вручную:

```bash
# Остановите текущий процесс (Ctrl+C или kill)
# Затем запустите снова
cd /opt/cloudtest
source venv/bin/activate
python run.py
```

## Шаг 4: Проверка работы

1. **Проверьте логи на ошибки:**
   ```bash
   sudo journalctl -u myapp.service -n 100 --no-pager
   ```

2. **Проверьте доступность приложения:**
   ```bash
   curl http://localhost:8000/health
   ```

3. **Проверьте миграции:**
   ```bash
   alembic current
   alembic history
   ```

4. **Откройте в браузере:**
   - Главная страница: `http://your-server-ip/cloud2/`
   - Каналы: `http://your-server-ip/cloud2/channels`
   - Создайте тестовый план в любом канале

## Возможные проблемы

### Ошибка: "Table 'plans' already exists"
Это означает, что миграция уже применена. Проверьте:
```bash
alembic current
```

### Ошибка: "No such revision: 011"
Убедитесь, что файл `alembic/versions/011_add_plans.py` скопирован на сервер.

### Ошибка импорта модулей
Убедитесь, что все новые файлы скопированы:
- `app/models/plan.py`
- `app/models/plan_item.py`
- `app/schemas/plan.py`
- `app/services/plan_service.py`
- `app/services/embed_service.py`
- `app/routers/plans.py`
- `app/routers/embed.py`
- Все шаблоны в `app/templates/`

### Ошибка: "ModuleNotFoundError: No module named 'app.models.plan'"
Проверьте, что файл `app/models/__init__.py` обновлен и содержит импорты Plan и PlanItem.

## Быстрая проверка всех файлов

```bash
# Проверьте наличие всех новых файлов
ls -la app/models/plan*.py
ls -la app/schemas/plan.py
ls -la app/services/plan_service.py
ls -la app/services/embed_service.py
ls -la app/routers/plans.py
ls -la app/routers/embed.py
ls -la app/templates/plan*.html
ls -la app/templates/embed*.html
ls -la app/templates/channel_plans.html
ls -la alembic/versions/011_add_plans.py
```

## Откат изменений (если что-то пошло не так)

```bash
# Откатить последнюю миграцию
alembic downgrade -1

# Или откатить до конкретной ревизии
alembic downgrade 010
```

