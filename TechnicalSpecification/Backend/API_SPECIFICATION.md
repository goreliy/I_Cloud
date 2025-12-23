# Техническое задание: Backend API

## Общая информация

Backend API системы IBolid Cloud построен на FastAPI и предоставляет REST API для работы с IoT данными, управления каналами, виджетами, автоматизацией и администрирования системы.

## Базовые принципы

### Формат данных
- **Входные данные**: JSON (для POST/PUT запросов), Query параметры (для GET запросов)
- **Выходные данные**: JSON (по умолчанию), XML, CSV (для экспорта данных)
- **Кодировка**: UTF-8

### Аутентификация

#### JWT токены (для веб-интерфейса)
- **Метод**: Bearer Token
- **Заголовок**: `Authorization: Bearer <token>`
- **Время жизни**: настраивается через `ACCESS_TOKEN_EXPIRE_MINUTES` (по умолчанию 30 минут)
- **Алгоритм**: HS256

#### API ключи (для устройств)
- **Типы**: `read` (чтение), `write` (запись)
- **Передача**: Query параметр `api_key` или заголовок `X-API-Key`
- **Кэширование**: TTL 60 секунд

### Коды ответов
- `200 OK` — успешный запрос
- `201 Created` — ресурс создан
- `204 No Content` — успешное удаление
- `400 Bad Request` — неверный запрос
- `401 Unauthorized` — требуется аутентификация
- `403 Forbidden` — недостаточно прав
- `404 Not Found` — ресурс не найден
- `429 Too Many Requests` — превышен лимит запросов
- `500 Internal Server Error` — внутренняя ошибка сервера

## Модули API

### 1. Модуль аутентификации (`/api/auth`)

#### POST `/api/auth/register`
Регистрация нового пользователя.

**Тело запроса:**
```json
{
  "email": "user@example.com",
  "password": "secure_password"
}
```

**Ответ:**
```json
{
  "id": 1,
  "email": "user@example.com",
  "is_active": true,
  "is_admin": false,
  "created_at": "2025-12-23T10:00:00Z"
}
```

#### POST `/api/auth/login`
Вход в систему и получение JWT токена.

**Тело запроса:**
```json
{
  "email": "user@example.com",
  "password": "secure_password"
}
```

**Ответ:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer"
}
```

#### GET `/api/auth/me`
Получение информации о текущем пользователе.

**Заголовки:**
- `Authorization: Bearer <token>`

**Ответ:**
```json
{
  "id": 1,
  "email": "user@example.com",
  "is_active": true,
  "is_admin": false,
  "created_at": "2025-12-23T10:00:00Z"
}
```

---

### 2. Модуль каналов (`/api/channels`)

#### POST `/api/channels`
Создание нового канала.

**Тело запроса:**
```json
{
  "name": "Мой канал",
  "description": "Описание канала",
  "public": true,
  "timezone": "UTC"
}
```

**Ответ:**
```json
{
  "id": 1,
  "name": "Мой канал",
  "description": "Описание канала",
  "public": true,
  "timezone": "UTC",
  "user_id": 1,
  "created_at": "2025-12-23T10:00:00Z"
}
```

#### GET `/api/channels`
Получение списка каналов.

**Query параметры:**
- `skip` (int, default: 0) — пропустить записей
- `limit` (int, default: 100) — максимум записей

**Ответ:**
```json
[
  {
    "id": 1,
    "name": "Мой канал",
    "public": true,
    "user_id": 1
  }
]
```

#### GET `/api/channels/{channel_id}`
Получение информации о канале.

**Ответ:**
```json
{
  "id": 1,
  "name": "Мой канал",
  "description": "Описание",
  "public": true,
  "timezone": "UTC",
  "field1_label": "Температура",
  "field2_label": "Влажность",
  "image_url": "/static/uploads/channels/1/image.jpg",
  "background_url": "/static/uploads/channels/1/background.jpg",
  "color_scheme": "light",
  "custom_css": "...",
  "created_at": "2025-12-23T10:00:00Z"
}
```

#### PUT `/api/channels/{channel_id}`
Обновление канала (только владелец).

**Тело запроса:**
```json
{
  "name": "Новое название",
  "description": "Новое описание",
  "public": false,
  "field1_label": "Температура",
  "field2_label": "Влажность"
}
```

#### DELETE `/api/channels/{channel_id}`
Удаление канала (только владелец).

**Ответ:** `204 No Content`

#### POST `/api/channels/{channel_id}/api-keys`
Создание API ключа для канала.

**Тело запроса:**
```json
{
  "type": "write",
  "name": "Устройство 1"
}
```

**Ответ:**
```json
{
  "id": 1,
  "key": "ABC123XYZ",
  "type": "write",
  "name": "Устройство 1",
  "is_active": true,
  "created_at": "2025-12-23T10:00:00Z"
}
```

#### GET `/api/channels/{channel_id}/api-keys`
Получение списка API ключей канала.

#### DELETE `/api/channels/{channel_id}/api-keys/{key_id}`
Удаление API ключа.

---

### 3. Модуль данных (Feeds) (`/feeds`, `/update`)

#### POST `/update` или GET `/update`
Запись данных в канал (ThingSpeak совместимый API).

**Query параметры:**
- `api_key` (required) — write API ключ
- `field1` до `field8` (optional, float) — данные полей
- `latitude` (optional, float) — широта
- `longitude` (optional, float) — долгота
- `elevation` (optional, float) — высота
- `status` (optional, string) — статусное сообщение

**Пример GET:**
```
GET /update?api_key=ABC123&field1=25.5&field2=60.2&latitude=55.7558&longitude=37.6173
```

**Пример POST:**
```json
{
  "api_key": "ABC123",
  "field1": 25.5,
  "field2": 60.2,
  "latitude": 55.7558,
  "longitude": 37.6173,
  "status": "OK"
}
```

**Ответ:**
```json
{
  "entry_id": 123
}
```

#### GET `/channels/{channel_id}/feeds.json`
Получение данных канала в формате JSON.

**Query параметры:**
- `results` (int, default: 100) — количество записей
- `start` (datetime) — начальная дата
- `end` (datetime) — конечная дата
- `average` (int) — агрегация по N записям
- `sum` (int) — сумма по N записям
- `median` (int) — медиана по N записям
- `min` (int) — минимум по N записям
- `max` (int) — максимум по N записям

**Аутентификация:**
- JWT токен (для веб-интерфейса)
- Read API ключ через `api_key` параметр

**Ответ:**
```json
{
  "channel": {
    "id": 1,
    "name": "Мой канал",
    "field1": "Температура",
    "field2": "Влажность"
  },
  "feeds": [
    {
      "entry_id": 123,
      "created_at": "2025-12-23T10:00:00Z",
      "field1": 25.5,
      "field2": 60.2,
      "latitude": 55.7558,
      "longitude": 37.6173,
      "status": "OK"
    }
  ]
}
```

#### GET `/channels/{channel_id}/feeds.csv`
Экспорт данных в CSV формат.

#### GET `/channels/{channel_id}/feeds.xml`
Экспорт данных в XML формат.

---

### 4. Модуль виджетов (`/api/channels/{channel_id}/widgets`)

#### POST `/api/channels/{channel_id}/widgets`
Создание виджета.

**Form Data:**
- `name` (string, required) — название виджета
- `widget_type` (string, default: "svg") — тип виджета (svg/html)
- `width` (int, default: 6) — ширина в колонках Bootstrap
- `height` (int, default: 300) — высота в пикселях
- `svg_bindings` (string, JSON) — привязки данных к SVG элементам
- `html_code` (string) — HTML код (для html виджетов)
- `css_code` (string) — CSS код
- `js_code` (string) — JavaScript код
- `file` (file) — SVG файл (для svg виджетов)
- `ai_service_id` (int, optional) — ID AI сервиса для генерации
- `prompt_used` (string, optional) — использованный промпт

**Ответ:**
```json
{
  "id": 1,
  "name": "Термометр",
  "widget_type": "svg",
  "width": 6,
  "height": 300,
  "svg_url": "/static/uploads/channels/1/svg/widget_abc123.svg",
  "svg_bindings": "[{\"element\":\"temp-value\",\"field\":\"field1\",\"format\":\"{value}°C\"}]",
  "created_at": "2025-12-23T10:00:00Z"
}
```

#### GET `/api/channels/{channel_id}/widgets`
Получение списка виджетов канала.

#### GET `/api/channels/{channel_id}/widgets/{widget_id}`
Получение информации о виджете.

#### PUT `/api/channels/{channel_id}/widgets/{widget_id}`
Обновление виджета.

#### DELETE `/api/channels/{channel_id}/widgets/{widget_id}`
Удаление виджета.

#### GET `/api/channels/{channel_id}/widgets/{widget_id}/versions`
Получение истории версий виджета.

---

### 5. Модуль AI сервисов (`/api/ai-services`)

#### POST `/api/ai-services`
Создание AI сервиса (только администратор).

**Тело запроса:**
```json
{
  "alias": "openai",
  "name": "OpenAI GPT",
  "provider": "openai",
  "api_key": "sk-...",
  "model": "gpt-4",
  "base_url": "https://api.openai.com/v1",
  "scope": "global",
  "is_active": true
}
```

#### GET `/api/ai-services`
Получение списка AI сервисов.

#### POST `/api/ai-services/{service_id}/generate-widget`
Генерация виджета с помощью AI.

**Тело запроса:**
```json
{
  "channel_id": 1,
  "prompt": "Создай термометр для отображения температуры",
  "widget_type": "svg"
}
```

#### POST `/api/ai-services/refine-prompt`
Улучшение промпта на основе обратной связи.

---

### 6. Модуль автоматизации (`/api/channels/{channel_id}/automation`)

#### POST `/api/channels/{channel_id}/automation`
Создание правила автоматизации.

**Тело запроса:**
```json
{
  "name": "Контроль температуры",
  "rule_type": "threshold",
  "priority": 1,
  "trigger_field": "field1",
  "condition": ">",
  "threshold_value": 30.0,
  "target_field": "field2",
  "action_type": "set_value",
  "action_value": 100.0
}
```

**Типы правил:**
- `threshold` — пороговое значение
- `pid` — PID контроллер
- `expression` — вычисление по выражению

**Ответ:**
```json
{
  "id": 1,
  "name": "Контроль температуры",
  "rule_type": "threshold",
  "priority": 1,
  "trigger_field": "field1",
  "condition": ">",
  "threshold_value": 30.0,
  "is_active": true,
  "created_at": "2025-12-23T10:00:00Z"
}
```

#### GET `/api/channels/{channel_id}/automation`
Получение списка правил автоматизации.

#### PUT `/api/channels/{channel_id}/automation/{rule_id}`
Обновление правила.

#### DELETE `/api/channels/{channel_id}/automation/{rule_id}`
Удаление правила.

---

### 7. Модуль администрирования (`/api/admin`)

#### GET `/api/admin/stats`
Получение статистики системы (только администратор).

**Ответ:**
```json
{
  "total_users": 100,
  "active_users": 50,
  "total_channels": 200,
  "public_channels": 150,
  "total_feeds": 10000,
  "recent_feeds_24h": 500,
  "recent_requests_24h": 1000,
  "avg_response_time": 45.2,
  "cpu_percent": 25.5,
  "memory_percent": 60.0,
  "disk_percent": 40.0
}
```

#### GET `/api/admin/users`
Получение списка пользователей с фильтрацией и сортировкой.

**Query параметры:**
- `skip` (int, default: 0)
- `limit` (int, default: 100)
- `sort` (string, default: "created_at")
- `order` (string, default: "desc") — "asc" или "desc"
- `search` (string) — поиск по email

#### GET `/api/admin/channels`
Получение списка всех каналов.

#### GET `/api/admin/requests`
Получение логов API запросов.

**Query параметры:**
- `skip` (int, default: 0)
- `limit` (int, default: 100)
- `start_date` (datetime)
- `end_date` (datetime)
- `method` (string) — фильтр по HTTP методу
- `status_code` (int) — фильтр по коду ответа

#### PUT `/api/admin/users/{user_id}`
Обновление пользователя (активация/деактивация, права администратора).

#### DELETE `/api/admin/users/{user_id}`
Удаление пользователя.

---

### 8. Модуль архивации (`/api/admin/archive`)

#### GET `/api/admin/archive/config`
Получение конфигурации архивации (только администратор).

#### PUT `/api/admin/archive/config`
Обновление конфигурации архивации.

**Тело запроса:**
```json
{
  "enabled": true,
  "backend_type": "sqlite",
  "sqlite_file_path": "archive/archive.db",
  "retention_days": 30,
  "schedule_interval_seconds": 3600,
  "copy_then_delete": true
}
```

#### POST `/api/admin/archive/run-now`
Запуск архивации вручную.

---

### 9. Модуль управления виджетами (`/api/control`)

#### POST `/api/control/widget/{widget_id}/execute`
Безопасное выполнение JavaScript кода виджета.

**Тело запроса:**
```json
{
  "action": "update",
  "data": {
    "field1": 25.5,
    "field2": 60.2
  }
}
```

---

### 10. Модуль стресс-тестирования (`/api/stress-test`)

#### POST `/api/stress-test/run`
Запуск стресс-теста (только администратор).

**Тело запроса:**
```json
{
  "url": "http://localhost:8000/update",
  "method": "GET",
  "workers": 10,
  "rps": 100,
  "duration_seconds": 60,
  "params": {
    "api_key": "test_key",
    "field1": 25.5
  }
}
```

#### GET `/api/stress-test/results/{test_id}`
Получение результатов стресс-теста.

---

## Middleware

### Request Logging Middleware
Логирует все API запросы в таблицу `request_logs`:
- URL
- HTTP метод
- Код ответа
- Время ответа
- IP адрес
- User-Agent

### Rate Limiting Middleware
Ограничивает количество запросов (только в production):
- По умолчанию: 100 запросов в минуту на IP
- Настраивается через конфигурацию

### CORS Middleware
Настраивается через `CORS_ORIGINS` в конфигурации.

### Root Path Middleware
Поддержка работы за реверс-прокси через `ROOT_PATH`.

---

## Обработка ошибок

### Стандартный формат ошибки
```json
{
  "detail": "Описание ошибки"
}
```

### Примеры ошибок
- `401 Unauthorized`: "Invalid API key"
- `403 Forbidden`: "Access denied to private channel"
- `404 Not Found`: "Channel not found"
- `400 Bad Request`: "Invalid field value"

---

## Производительность

### In-Memory Buffer
Для оптимизации записи данных используется буфер:
- Максимум 50,000 записей в очереди
- Размер батча: 200 записей
- Интервал сброса: 100ms
- Максимальная задержка: 500ms

### Кэширование
- API ключи кэшируются на 60 секунд
- Используется in-memory кэш

### Пул соединений
- Размер пула: 50 соединений
- Максимальный overflow: 100
- Таймаут: 60 секунд

---

## Безопасность

### Валидация данных
- Все входные данные валидируются через Pydantic схемы
- SQL инъекции предотвращаются через SQLAlchemy ORM
- XSS защита через экранирование в шаблонах

### Аутентификация
- JWT токены с секретным ключом
- API ключи хранятся в хешированном виде
- Пароли хешируются через bcrypt

### Авторизация
- Проверка прав доступа к каналам
- Владелец канала имеет полный доступ
- Публичные каналы доступны всем (если AUTH_ENABLED=false)

---

## Документация API

Автоматическая документация доступна по адресам:
- **Swagger UI**: `/docs`
- **ReDoc**: `/redoc`

Документация генерируется автоматически из docstrings и схем Pydantic.

