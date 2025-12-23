# Тестирование API планов

## Проблема: 404 на `/cloud2/api/channels/1/plans`

Запрос идет с префиксом `/cloud2`, но FastAPI ожидает `/api/channels/1/plans`.

## Тест 1: Прямой запрос (минуя nginx)

```bash
# На сервере приложения (192.168.66.205)
curl -X POST "http://localhost:8000/api/channels/1/plans" \
  -H "Content-Type: application/json" \
  -d '{"name": "Тест", "description": "", "is_default": false}'
```

Если это работает - проблема в nginx конфигурации.

## Тест 2: Через nginx (с префиксом)

```bash
# С внешнего IP или с прокси-сервера
curl -X POST "http://your-external-ip/cloud2/api/channels/1/plans" \
  -H "Content-Type: application/json" \
  -d '{"name": "Тест", "description": "", "is_default": false}'
```

## Проверка nginx конфигурации

На прокси-сервере проверьте файл конфигурации nginx. Должно быть:

```nginx
location /cloud2/ {
   rewrite  ^/cloud2/(.*)  /$1 break;
   proxy_pass http://192.168.66.205:8000;
}
```

**Важно**: `rewrite` должен быть **перед** `proxy_pass` и использовать флаг `break`.

## Возможное решение

Если nginx правильно настроен, но запрос все равно идет с префиксом, возможно проблема в том, что:
1. JavaScript отправляет запрос напрямую на сервер приложения (минуя nginx)
2. Или nginx не применяет rewrite для POST запросов

Проверьте в браузере (F12 → Network) - на какой URL идет запрос.

