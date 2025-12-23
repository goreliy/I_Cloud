# Настройка работы за реверс-прокси (nginx)

## Проблема
При работе за реверс-прокси с префиксом пути (например, `/cloud2`) возникают ошибки "Not Found", так как:
1. JavaScript код использует абсолютные пути (`/api/...`, `/channels/...`)
2. Статические файлы ссылаются на абсолютные пути (`/static/...`)
3. FastAPI не знает о префиксе пути

## Решение

### 1. Настройка приложения

На сервере, где запущено приложение (`192.168.66.205`):

1. Откройте файл `.env` в корне проекта
2. Добавьте строку:
   ```env
   ROOT_PATH=/cloud2
   ```
3. Перезапустите приложение

### 2. Настройка nginx

В файле `other_revers_proxy_nginx_conf/conf.d/default.conf` уже настроено:

```nginx
location /cloud2/ {
   rewrite  ^/cloud2/(.*)  /$1 break;
   proxy_set_header X-Is-Reverse-Proxy "true";
   proxy_set_header Host $host;
   proxy_set_header X-Real-IP $remote_addr;
   proxy_set_header X-Forwarded-For $remote_addr;
   proxy_set_header X-Forwarded-Proto $scheme;
   proxy_set_header X-Forwarded-Prefix /cloud2;
   proxy_pass http://192.168.66.205:8000;
}

location = /cloud2 {
   return 301 /cloud2/;
}
```

**Важно**: Эта конфигурация должна быть в обоих блоках `server` (HTTP на порту 80 и HTTPS на порту 443).

### 3. Применение изменений

1. **На прокси-сервере** (где nginx):
   ```bash
   # Проверка конфигурации
   nginx -t
   
   # Перезагрузка nginx
   nginx -s reload
   # или
   systemctl reload nginx
   ```

2. **На сервере приложения** (`192.168.66.205`):
   ```bash
   # Убедитесь, что в .env есть ROOT_PATH=/cloud2
   cat .env | grep ROOT_PATH
   
   # Перезапустите приложение
   # Если используете systemd:
   systemctl restart ibolid-cloud
   
   # Или если запускаете вручную:
   # Остановите (Ctrl+C) и запустите снова:
   python run.py
   ```

## Как это работает

1. **Nginx** получает запрос на `/cloud2/...`
2. **Rewrite** удаляет префикс `/cloud2`, оставляя только путь (например, `/cloud2/api/test` → `/api/test`)
3. Запрос проксируется на приложение без префикса
4. **RootPathMiddleware** автоматически добавляет префикс `/cloud2` ко всем абсолютным путям в HTML:
   - HTML атрибуты: `href="/path"` → `href="/cloud2/path"`
   - JavaScript: `fetch('/api/...')` → `fetch('/cloud2/api/...')`
   - Статические файлы: `src="/static/..."` → `src="/cloud2/static/..."`

## Проверка

После настройки проверьте:

1. Откройте браузер и перейдите на `http://ваш-белый-ip/cloud2/`
2. Должна открыться главная страница приложения
3. Проверьте в Developer Tools (F12) → Network:
   - Все запросы должны идти на `/cloud2/...`
   - Статические файлы должны загружаться с `/cloud2/static/...`
   - API запросы должны идти на `/cloud2/api/...`

## Отладка

Если что-то не работает:

1. **Проверьте логи nginx**:
   ```bash
   tail -f /var/log/nginx/error.log
   ```

2. **Проверьте логи приложения**:
   ```bash
   # Если через systemd:
   journalctl -u ibolid-cloud -f
   
   # Если вручную - смотрите вывод в консоли
   ```

3. **Проверьте, что ROOT_PATH установлен**:
   ```bash
   # В консоли Python при запуске должно быть:
   # Root path configured: /cloud2
   ```

4. **Проверьте заголовки запросов**:
   - Откройте Developer Tools → Network
   - Посмотрите на запросы - они должны идти на правильные пути

## Альтернативные префиксы

Если нужно использовать другой префикс (например, `/myapp`):

1. В `.env` установите: `ROOT_PATH=/myapp`
2. В nginx измените `location /cloud2/` на `location /myapp/`
3. В rewrite измените: `rewrite  ^/myapp/(.*)  /$1 break;`
4. В proxy_set_header: `proxy_set_header X-Forwarded-Prefix /myapp;`

