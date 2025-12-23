# Исправление проблемы с планами

## Проблема 1: Таблицы не созданы

Миграция не применена. Нужно применить миграцию:

```bash
cd /home/gorelyi/CloudTest
source venv/bin/activate

# Проверить текущую ревизию
alembic current

# Применить миграцию
alembic upgrade head

# Проверить, что таблицы созданы
sqlite3 ibolid.db "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'plan%';"
```

Должны появиться таблицы:
- `plans`
- `plan_items`

## Проблема 2: 404 на API запросы

В логах видно, что запрос идет на `/cloud2/api/channels/1/plans`, но получает 404.

Это означает, что либо:
1. Nginx не делает rewrite правильно
2. Запрос идет напрямую на сервер приложения, минуя nginx

### Проверка nginx конфигурации

На прокси-сервере проверьте, что в nginx есть rewrite:

```nginx
location /cloud2/ {
   rewrite  ^/cloud2/(.*)  /$1 break;
   proxy_pass http://192.168.66.205:8000;
}
```

### Проверка ROOT_PATH

На сервере приложения проверьте `.env`:

```bash
grep ROOT_PATH .env
```

Должно быть:
```
ROOT_PATH=/cloud2
```

### Тест напрямую

Попробуйте сделать запрос напрямую на сервер приложения (минуя nginx):

```bash
curl -X POST "http://192.168.66.205:8000/api/channels/1/plans" \
  -H "Content-Type: application/json" \
  -d '{"name": "Тест", "description": "", "is_default": false}'
```

Если это работает, значит проблема в nginx конфигурации.

## После исправления

1. Примените миграцию
2. Перезапустите сервис:
   ```bash
   sudo systemctl restart myapp.service
   ```
3. Проверьте логи:
   ```bash
   sudo journalctl -u myapp.service -f
   ```

