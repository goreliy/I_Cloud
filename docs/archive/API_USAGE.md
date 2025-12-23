# API Usage Guide / Руководство по использованию API

## Обзор

ThingSpeak FastAPI Clone предоставляет REST API, совместимый с оригинальным ThingSpeak API.

## Базовый URL

```
http://localhost:8000
```

## Аутентификация

Приложение поддерживает два режима работы:

### 1. С аутентификацией (AUTH_ENABLED=true)

- **JWT токены** для веб-интерфейса
- **API ключи** для записи/чтения данных
- Требуется регистрация пользователей

### 2. Без аутентификации (AUTH_ENABLED=false)

- Открытый доступ ко всем endpoints
- API ключи опциональны
- Не требуется регистрация

---

## Endpoints

### 🔐 Аутентификация (только если AUTH_ENABLED=true)

#### Регистрация

```http
POST /api/auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "securepassword"
}
```

**Ответ:**
```json
{
  "id": 1,
  "email": "user@example.com",
  "is_active": true,
  "is_admin": false,
  "created_at": "2024-01-01T00:00:00"
}
```

#### Вход

```http
POST /api/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "securepassword"
}
```

**Ответ:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

#### Получить информацию о текущем пользователе

```http
GET /api/auth/me
Authorization: Bearer <access_token>
```

---

### 📡 Управление каналами

#### Создать канал

```http
POST /api/channels
Authorization: Bearer <access_token>  # если AUTH_ENABLED=true
Content-Type: application/json

{
  "name": "Temperature Sensor",
  "description": "Room temperature and humidity monitoring",
  "public": true,
  "timezone": "UTC"
}
```

**Ответ:**
```json
{
  "id": 1,
  "user_id": 1,
  "name": "Temperature Sensor",
  "description": "Room temperature and humidity monitoring",
  "public": true,
  "timezone": "UTC",
  "last_entry_id": 0,
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:00"
}
```

#### Получить список каналов

```http
GET /api/channels?skip=0&limit=100
```

#### Получить информацию о канале

```http
GET /api/channels/{channel_id}
```

#### Обновить канал

```http
PUT /api/channels/{channel_id}
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "name": "Updated Name",
  "description": "Updated description"
}
```

#### Удалить канал

```http
DELETE /api/channels/{channel_id}
Authorization: Bearer <access_token>
```

---

### 🔑 API ключи

#### Получить API ключи канала

```http
GET /api/channels/{channel_id}/api-keys
Authorization: Bearer <access_token>
```

**Ответ:**
```json
[
  {
    "id": 1,
    "channel_id": 1,
    "key": "abc123def456...",
    "type": "write",
    "is_active": true,
    "created_at": "2024-01-01T00:00:00"
  },
  {
    "id": 2,
    "channel_id": 1,
    "key": "xyz789uvw012...",
    "type": "read",
    "is_active": true,
    "created_at": "2024-01-01T00:00:00"
  }
]
```

#### Создать новый API ключ

```http
POST /api/channels/{channel_id}/api-keys
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "type": "write"
}
```

---

### 📝 Запись данных (ThingSpeak Compatible)

#### Метод 1: GET запрос

```http
GET /update?api_key=YOUR_WRITE_KEY&field1=25.5&field2=60.2&field3=1013.25
```

**Пример с curl:**
```bash
curl "http://localhost:8000/update?api_key=YOUR_WRITE_KEY&field1=25.5&field2=60.2"
```

#### Метод 2: POST запрос

```http
POST /update
Content-Type: application/json

{
  "api_key": "YOUR_WRITE_KEY",
  "field1": 25.5,
  "field2": 60.2,
  "field3": 1013.25,
  "latitude": 55.7558,
  "longitude": 37.6173,
  "elevation": 156.0,
  "status": "Online"
}
```

**Пример с curl:**
```bash
curl -X POST "http://localhost:8000/update" \
  -H "Content-Type: application/json" \
  -d '{
    "api_key": "YOUR_WRITE_KEY",
    "field1": 25.5,
    "field2": 60.2
  }'
```

**Ответ:** Номер записи (entry_id)
```
123
```

#### Поля данных

- **field1-field8**: Числовые поля (Float)
- **latitude**: Широта (Float)
- **longitude**: Долгота (Float)
- **elevation**: Высота в метрах (Float)
- **status**: Текстовый статус (String)

---

### 📊 Чтение данных

#### Получить данные в JSON

```http
GET /channels/{channel_id}/feeds.json?results=100
```

**Параметры:**
- `results` - количество записей (1-8000, по умолчанию 100)
- `start` - начало периода (ISO 8601 datetime)
- `end` - конец периода (ISO 8601 datetime)
- `timescale` - агрегация по минутам
- `average` - среднее значение по минутам
- `median` - медиана
- `sum` - сумма по минутам
- `round` - округление до N знаков

**Примеры:**

```bash
# Последние 50 записей
curl "http://localhost:8000/channels/1/feeds.json?results=50"

# За последние 24 часа
curl "http://localhost:8000/channels/1/feeds.json?start=2024-01-01T00:00:00"

# С агрегацией по 10 минутам
curl "http://localhost:8000/channels/1/feeds.json?timescale=10"

# Среднее за каждые 15 минут
curl "http://localhost:8000/channels/1/feeds.json?average=15"

# Медиана
curl "http://localhost:8000/channels/1/feeds.json?median=1"

# Округление до 2 знаков
curl "http://localhost:8000/channels/1/feeds.json?round=2"
```

**Ответ:**
```json
{
  "channel": {
    "id": 1,
    "name": "Temperature Sensor",
    "description": "Room monitoring",
    "last_entry_id": 123
  },
  "feeds": [
    {
      "id": 123,
      "channel_id": 1,
      "entry_id": 123,
      "created_at": "2024-01-01T12:00:00",
      "field1": 25.5,
      "field2": 60.2,
      "field3": null,
      "field4": null,
      "field5": null,
      "field6": null,
      "field7": null,
      "field8": null,
      "latitude": null,
      "longitude": null,
      "elevation": null,
      "status": null
    }
  ]
}
```

#### Получить данные в XML

```http
GET /channels/{channel_id}/feeds.xml?results=100
```

```bash
curl "http://localhost:8000/channels/1/feeds.xml?results=10"
```

**Ответ:**
```xml
<?xml version="1.0" ?>
<channel>
  <id>1</id>
  <name>Temperature Sensor</name>
  <feeds>
    <feed>
      <id>123</id>
      <entry_id>123</entry_id>
      <created_at>2024-01-01T12:00:00</created_at>
      <field1>25.5</field1>
      <field2>60.2</field2>
    </feed>
  </feeds>
</channel>
```

#### Получить данные в CSV

```http
GET /channels/{channel_id}/feeds.csv?results=100
```

```bash
curl "http://localhost:8000/channels/1/feeds.csv?results=10"
```

**Ответ:**
```csv
entry_id,created_at,field1,field2,field3,field4,field5,field6,field7,field8,latitude,longitude,elevation,status
123,2024-01-01T12:00:00,25.5,60.2,,,,,,,,,,
122,2024-01-01T11:00:00,24.8,58.5,,,,,,,,,,
```

#### Получить последнюю запись

```http
GET /channels/{channel_id}/feeds/last.json
```

```bash
curl "http://localhost:8000/channels/1/feeds/last.json"
```

#### Получить данные конкретного поля

```http
GET /channels/{channel_id}/field/{field_num}.json?results=100
```

```bash
# Получить данные только из field1
curl "http://localhost:8000/channels/1/field/1.json?results=50"
```

---

### 👨‍💼 Админ панель (только для администраторов)

#### Получить статистику системы

```http
GET /api/admin/stats
Authorization: Bearer <admin_access_token>
```

**Ответ:**
```json
{
  "total_users": 10,
  "active_users": 8,
  "total_channels": 25,
  "public_channels": 20,
  "total_feeds": 15000,
  "recent_feeds_24h": 500
}
```

#### Получить список всех пользователей

```http
GET /api/admin/users?skip=0&limit=100
Authorization: Bearer <admin_access_token>
```

#### Получить список всех каналов

```http
GET /api/admin/channels?skip=0&limit=100
Authorization: Bearer <admin_access_token>
```

---

## Примеры использования

### Python

```python
import requests

# Создать канал
response = requests.post(
    "http://localhost:8000/api/channels",
    json={
        "name": "My Sensor",
        "description": "Temperature monitoring",
        "public": True
    },
    headers={"Authorization": f"Bearer {access_token}"}
)
channel = response.json()
print(f"Channel created: {channel['id']}")

# Отправить данные
write_key = "YOUR_WRITE_KEY"
requests.get(
    "http://localhost:8000/update",
    params={
        "api_key": write_key,
        "field1": 25.5,
        "field2": 60.2
    }
)

# Получить данные
response = requests.get(
    f"http://localhost:8000/channels/{channel['id']}/feeds.json",
    params={"results": 10}
)
data = response.json()
print(f"Received {len(data['feeds'])} entries")
```

### Arduino/ESP32

```cpp
#include <WiFi.h>
#include <HTTPClient.h>

const char* ssid = "YOUR_WIFI";
const char* password = "YOUR_PASSWORD";
const char* serverName = "http://your-server:8000/update";
const char* apiKey = "YOUR_WRITE_KEY";

void setup() {
  Serial.begin(115200);
  WiFi.begin(ssid, password);
  
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.println("Connecting to WiFi...");
  }
  Serial.println("Connected!");
}

void loop() {
  if(WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    
    float temperature = readTemperature();
    float humidity = readHumidity();
    
    String url = String(serverName) + "?api_key=" + apiKey +
                 "&field1=" + String(temperature) +
                 "&field2=" + String(humidity);
    
    http.begin(url);
    int httpCode = http.GET();
    
    if(httpCode > 0) {
      String payload = http.getString();
      Serial.println("Entry ID: " + payload);
    }
    
    http.end();
  }
  
  delay(60000); // Send every minute
}
```

### Node.js

```javascript
const axios = require('axios');

const baseURL = 'http://localhost:8000';
const writeKey = 'YOUR_WRITE_KEY';

// Отправить данные
async function sendData(field1, field2) {
  try {
    const response = await axios.get(`${baseURL}/update`, {
      params: {
        api_key: writeKey,
        field1,
        field2
      }
    });
    console.log('Entry ID:', response.data);
  } catch (error) {
    console.error('Error:', error.message);
  }
}

// Получить данные
async function getData(channelId) {
  try {
    const response = await axios.get(
      `${baseURL}/channels/${channelId}/feeds.json`,
      { params: { results: 10 } }
    );
    console.log('Data:', response.data);
  } catch (error) {
    console.error('Error:', error.message);
  }
}

// Использование
sendData(25.5, 60.2);
getData(1);
```

---

## Коды ответов

- **200 OK** - Успешный запрос
- **201 Created** - Ресурс создан
- **204 No Content** - Успешное удаление
- **400 Bad Request** - Неверные параметры запроса
- **401 Unauthorized** - Требуется аутентификация
- **403 Forbidden** - Недостаточно прав
- **404 Not Found** - Ресурс не найден
- **500 Internal Server Error** - Внутренняя ошибка сервера

---

## Лимиты

- Максимум 8000 записей за один запрос
- 8 полей данных на канал
- Рекомендуется не отправлять данные чаще 1 раза в секунду

---

## Документация

Интерактивная документация API доступна по адресам:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

