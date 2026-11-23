# PulseWatch — API Monitoring Service

## Что это

Сервис мониторинга доступности API и веб-сайтов. Пользователь добавляет URL-ы своих сервисов, система периодически проверяет их и алертит при проблемах.

Аналоги: UptimeRobot, Pingdom, healthchecks.io

---

## Функционал

### MVP (Stage 6-7)

**Пользователи:**
- Регистрация (email + password)
- JWT аутентификация (access + refresh token)
- Профиль пользователя

**Мониторы (checks):**
- CRUD для мониторов (создать, получить, обновить, удалить)
- Каждый монитор: URL, метод (GET/POST/HEAD), ожидаемый статус код, интервал проверки (30s / 1m / 5m / 15m), таймаут
- Опционально: заголовки запроса, тело запроса для POST
- Статус монитора: up / down / paused / pending

**Результаты проверок (check_results):**
- Хранение каждой проверки: статус код, время ответа (ms), ошибка если есть, timestamp
- История проверок за период (24h / 7d / 30d)
- Uptime в процентах за период

**Алерты:**
- Правила алертов: после N неудачных проверок подряд — алерт
- Каналы: email, webhook (POST на URL пользователя)
- История алертов: когда сработал, когда восстановился, длительность даунтайма

### Этап 2 (Stage 8 — Redis)

**Кэширование:**
- Текущий статус всех мониторов пользователя — в Redis (не ходить в БД на каждый запрос дашборда)
- Кэш агрегированных метрик (uptime за 24h) — инвалидация раз в минуту

**Rate limiting:**
- По API ключу: максимум N запросов в минуту
- По IP для auth эндпоинтов: защита от брутфорса

### Этап 3 (Stage 9 — Celery)

**Периодические задачи (Celery Beat):**
- Scheduler: запускает проверки по расписанию для каждого монитора
- Каждая проверка — отдельная Celery задача
- Параллельная проверка сотен URL через воркеры

**Фоновые задачи:**
- Отправка алертов (email, webhook) — через Celery, не блокируя API
- Retry при ошибке отправки (3 попытки с exponential backoff)
- Агрегация метрик: раз в час считать uptime, avg response time

**Dead letter queue:**
- Задачи которые упали после всех retry — в отдельную очередь для анализа

### Этап 4 (Stage 10 — Docker)

**docker-compose.yml:**
```
services:
  - app (FastAPI + uvicorn)
  - db (PostgreSQL)
  - redis (Redis)
  - celery-worker (Celery workers)
  - celery-beat (Celery scheduler)
  - migrations (Alembic — run once)
```

**Dockerfile:**
- Multi-stage build
- Non-root user
- Health check

### Этап 5 (Stage 11 — Тесты)

**Unit тесты:**
- Бизнес-логика: определение статуса монитора, расчёт uptime, логика алертов

**Integration тесты:**
- API тесты через TestClient
- Тесты с реальной БД (transaction rollback)
- Тесты Celery задач

**Coverage:** цель 80%+

### Этап 6 (Stage 13 — Архитектура)

**Рефакторинг по Cosmic Python:**
- Domain Model: Monitor, CheckResult, Alert, AlertRule
- Repository Pattern: абстракция доступа к данным
- Service Layer: бизнес-логика отдельно от роутеров
- Unit of Work: транзакционность

---

## Схема базы данных (предварительная)

### users
| Колонка | Тип | Описание |
|---------|-----|----------|
| id | BIGSERIAL PK | |
| email | VARCHAR(254) NOT NULL UNIQUE | |
| username | VARCHAR(50) NOT NULL | |
| password_hash | TEXT NOT NULL | |
| is_active | BOOLEAN DEFAULT true | |
| created_at | TIMESTAMPTZ DEFAULT now() | |

### monitors
| Колонка | Тип | Описание |
|---------|-----|----------|
| id | BIGSERIAL PK | |
| user_id | BIGINT FK → users ON DELETE CASCADE | владелец |
| name | VARCHAR(200) NOT NULL | человекочитаемое название |
| url | TEXT NOT NULL | URL для проверки |
| method | VARCHAR(10) DEFAULT 'GET' | HTTP метод |
| expected_status | INTEGER DEFAULT 200 | ожидаемый статус код |
| interval_seconds | INTEGER DEFAULT 300 | интервал проверки |
| timeout_seconds | INTEGER DEFAULT 10 | таймаут запроса |
| headers | JSONB | доп. заголовки |
| body | TEXT | тело запроса для POST |
| status | VARCHAR(20) DEFAULT 'pending' | up/down/paused/pending |
| is_active | BOOLEAN DEFAULT true | пауза монитора |
| created_at | TIMESTAMPTZ DEFAULT now() | |
| updated_at | TIMESTAMPTZ | |

### check_results
| Колонка | Тип | Описание |
|---------|-----|----------|
| id | BIGSERIAL PK | |
| monitor_id | BIGINT FK → monitors ON DELETE CASCADE | |
| status_code | INTEGER | полученный статус код (NULL если таймаут) |
| response_time_ms | INTEGER | время ответа в миллисекундах |
| is_success | BOOLEAN NOT NULL | прошла ли проверка |
| error_message | TEXT | ошибка если есть |
| checked_at | TIMESTAMPTZ DEFAULT now() | |

**Важно:** эта таблица будет огромной (миллионы строк). Нужны:
- INDEX на (monitor_id, checked_at DESC) — для выборки истории
- Partial INDEX на (monitor_id) WHERE is_success = false — для быстрого поиска ошибок
- Стратегия удаления старых данных (DELETE WHERE checked_at < 90 дней назад)

### alert_rules
| Колонка | Тип | Описание |
|---------|-----|----------|
| id | BIGSERIAL PK | |
| monitor_id | BIGINT FK → monitors ON DELETE CASCADE | |
| channel | VARCHAR(20) NOT NULL | email / webhook / telegram |
| target | TEXT NOT NULL | куда слать (email, URL, chat_id) |
| threshold | INTEGER DEFAULT 3 | после скольких неудач алертить |
| is_active | BOOLEAN DEFAULT true | |
| created_at | TIMESTAMPTZ DEFAULT now() | |

### alerts
| Колонка | Тип | Описание |
|---------|-----|----------|
| id | BIGSERIAL PK | |
| alert_rule_id | BIGINT FK → alert_rules ON DELETE CASCADE | |
| monitor_id | BIGINT FK → monitors ON DELETE CASCADE | |
| status | VARCHAR(20) NOT NULL | triggered / resolved |
| triggered_at | TIMESTAMPTZ NOT NULL DEFAULT now() | когда сработал |
| resolved_at | TIMESTAMPTZ | когда восстановился |
| downtime_seconds | INTEGER | длительность даунтайма |

---

## API эндпоинты

### Auth
```
POST   /auth/register        — регистрация
POST   /auth/login            — логин, получить токены
POST   /auth/refresh          — обновить access token
GET    /auth/me               — текущий пользователь
```

### Monitors
```
POST   /monitors              — создать монитор
GET    /monitors              — список мониторов пользователя
GET    /monitors/{id}         — детали монитора + текущий статус
PATCH  /monitors/{id}         — обновить настройки
DELETE /monitors/{id}         — удалить монитор
POST   /monitors/{id}/pause   — поставить на паузу
POST   /monitors/{id}/resume  — возобновить
```

### Check Results
```
GET    /monitors/{id}/results          — история проверок (пагинация)
GET    /monitors/{id}/results/summary  — агрегированная статистика (uptime %, avg response time)
```

### Alert Rules
```
POST   /monitors/{id}/alerts          — создать правило алерта
GET    /monitors/{id}/alerts          — список правил
PATCH  /monitors/{id}/alerts/{aid}    — изменить правило
DELETE /monitors/{id}/alerts/{aid}    — удалить правило
```

### Alerts History
```
GET    /alerts                — все алерты пользователя (фильтр по статусу, дате)
GET    /alerts/{id}           — детали алерта
```

### Dashboard
```
GET    /dashboard             — общая картина: все мониторы + текущий статус + uptime 24h
```

---

## Технический стек

| Компонент | Технология |
|-----------|-----------|
| API | FastAPI + Uvicorn |
| ORM | SQLAlchemy 2.0 (async) |
| БД | PostgreSQL 16 |
| Миграции | Alembic |
| Кэш | Redis |
| Очереди | Celery + Redis (broker) |
| Scheduler | Celery Beat |
| HTTP клиент | httpx (async) |
| Контейнеризация | Docker + docker-compose |
| Тесты | pytest + pytest-asyncio |
| Линтер | ruff |
| Type checking | mypy |

---

## Структура проекта (финальная, после рефакторинга)

```
monitoring_service/
├── docker-compose.yml
├── Dockerfile
├── alembic/
├── src/
│   ├── main.py                  # FastAPI app, lifespan, middleware
│   ├── config.py                # Settings (pydantic-settings)
│   ├── domain/                  # Domain models (чистые Python классы)
│   │   ├── monitor.py
│   │   ├── check_result.py
│   │   └── alert.py
│   ├── service/                 # Business logic (Service Layer)
│   │   ├── monitor_service.py
│   │   ├── checker_service.py
│   │   └── alert_service.py
│   ├── repository/              # Data access (Repository Pattern)
│   │   ├── base.py
│   │   ├── monitor_repo.py
│   │   └── alert_repo.py
│   ├── api/                     # FastAPI routers
│   │   ├── auth.py
│   │   ├── monitors.py
│   │   ├── results.py
│   │   ├── alerts.py
│   │   └── dashboard.py
│   ├── models/                  # SQLAlchemy ORM models
│   │   ├── base.py
│   │   ├── user.py
│   │   ├── monitor.py
│   │   ├── check_result.py
│   │   └── alert.py
│   ├── schemas/                 # Pydantic schemas (request/response)
│   │   ├── user.py
│   │   ├── monitor.py
│   │   ├── check_result.py
│   │   └── alert.py
│   ├── tasks/                   # Celery tasks
│   │   ├── checker.py           # HTTP check task
│   │   ├── alerter.py           # Send alert task
│   │   └── aggregator.py        # Metrics aggregation task
│   ├── deps.py                  # FastAPI dependencies (db session, current user)
│   └── exceptions.py            # Custom exceptions
├── tests/
│   ├── conftest.py
│   ├── test_api/
│   ├── test_service/
│   └── test_tasks/
├── pyproject.toml
└── README.md
```

---

## Что это покажет работодателю

1. **Архитектура** — слоёная структура, не всё в роутерах
2. **PostgreSQL** — сложная схема, индексы, работа с большими таблицами
3. **Async** — async FastAPI + async SQLAlchemy + httpx
4. **Background processing** — Celery workers, Beat scheduler, retry, dead letters
5. **Кэширование** — Redis для статусов и rate limiting
6. **Docker** — полный docker-compose, multi-stage Dockerfile
7. **Тесты** — unit + integration + API tests
8. **Мониторинг** — ты не просто пишешь API, ты понимаешь reliability
9. **Код** — чистый, типизированный, по паттернам из Cosmic Python
