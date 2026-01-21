# NIGINart Analytics Dashboard

Система аналитики социальных сетей для бренда NIGINart. Сбор, хранение и визуализация метрик из 8 платформ: Telegram, YouTube, VK, TikTok, Instagram, Дзен, Wibes и Pinterest.

## 📋 Содержание

- [Архитектура проекта](#архитектура-проекта)
- [Технологический стек](#технологический-стек)
- [Структура проекта](#структура-проекта)
- [Установка и запуск](#установка-и-запуск)
- [Конфигурация](#конфигурация)
- [API документация](#api-документация)
- [База данных](#база-данных)
- [Парсеры платформ](#парсеры-платформ)
- [Dashboard](#dashboard)
- [Разработка](#разработка)
- [Деплой](#деплой)

---

## 🏗️ Архитектура проекта

Проект состоит из трех основных компонентов:

1. **FastAPI Backend** (`src/`) - REST API, парсеры, scheduler
2. **PostgreSQL Database** - хранение метрик и конфигураций
3. **Streamlit Dashboard** (`dashboard/`) - визуализация данных

```
┌─────────────────┐      ┌──────────────────┐      ┌─────────────────┐
│   Социальные    │─────▶│  FastAPI + APScheduler │─────▶│   PostgreSQL    │
│    платформы    │      │   (Парсеры)      │      │    Database     │
└─────────────────┘      └──────────────────┘      └─────────────────┘
                                  │                          │
                                  │                          │
                                  ▼                          ▼
                         ┌──────────────────┐      ┌─────────────────┐
                         │   REST API       │◀─────│  Streamlit      │
                         │   /api/v1/*      │      │   Dashboard     │
                         └──────────────────┘      └─────────────────┘
```

---

## 🛠️ Технологический стек

### Backend
- **FastAPI** 0.109+ - веб-фреймворк
- **SQLAlchemy** 2.0+ - ORM
- **Alembic** - миграции БД
- **APScheduler** - планировщик задач
- **asyncpg** - асинхронный PostgreSQL драйвер
- **Pydantic** 2.5+ - валидация данных

### Database
- **PostgreSQL** 16+ - основная БД

### Парсеры
- **Telethon** - Telegram API
- **Google API Client** - YouTube Data API
- **vk-api / vkbottle** - VK API
- **TikTok Display API** - официальное API TikTok (OAuth)
- **Instagram Graph API** - официальное API Instagram (OAuth)
- **Playwright** - веб-скрапинг (Дзен, Wibes, Pinterest)
- **httpx / aiohttp** - HTTP-клиенты

### Dashboard
- **Streamlit** 1.31+ - интерфейс
- **Plotly** - интерактивные графики
- **Pandas** - обработка данных

### DevOps
- **Docker** + **Docker Compose** - контейнеризация
- **Nginx** - reverse proxy (production)

---

## 📁 Структура проекта

```
dashboard_v2/
├── src/                          # Backend приложение
│   ├── main.py                   # Точка входа FastAPI
│   ├── config/                   # Конфигурация
│   │   ├── settings.py           # Настройки из .env
│   │   └── security.py           # Шифрование токенов
│   ├── db/                       # База данных
│   │   ├── session.py            # Async session factory
│   │   └── init_db.py            # Инициализация БД
│   ├── models/                   # SQLAlchemy модели
│   │   ├── account.py            # Аккаунты соцсетей
│   │   ├── metric.py             # Метрики
│   │   ├── oauth.py              # OAuth credentials
│   │   └── collection_log.py     # Логи сборов
│   ├── api/                      # REST API
│   │   └── routers/              # Эндпоинты
│   │       ├── accounts.py       # CRUD аккаунтов
│   │       ├── metrics.py        # Получение метрик
│   │       ├── oauth.py          # OAuth flows
│   │       └── health.py         # Healthcheck
│   ├── parsers/                  # Парсеры платформ
│   │   ├── base.py               # Базовый класс парсера
│   │   ├── telegram.py           # Telegram парсер
│   │   ├── youtube.py            # YouTube парсер
│   │   ├── vk.py                 # VK парсер
│   │   ├── tiktok.py             # TikTok API парсер
│   │   ├── instagram.py          # Instagram API парсер
│   │   ├── dzen.py               # Дзен веб-парсер
│   │   ├── wibes.py              # Wibes веб-парсер
│   │   └── pinterest.py          # Pinterest веб-парсер
│   ├── scheduler/                # APScheduler
│   │   ├── tasks.py              # Задачи сбора метрик
│   │   └── scheduler.py          # Конфигурация scheduler
│   └── services/                 # Бизнес-логика
│       ├── account_service.py    # Сервис аккаунтов
│       ├── metric_service.py     # Сервис метрик
│       └── instagram/            # Instagram сервисы
│           ├── story_service.py  # Сбор stories
│           └── performance.py    # Оптимизация запросов
│
├── dashboard/                    # Streamlit интерфейс
│   ├── app.py                    # Главная страница
│   ├── config.py                 # Конфигурация dashboard
│   ├── pages/                    # Страницы платформ
│   │   ├── telegram.py           # Аналитика Telegram
│   │   ├── youtube.py            # Аналитика YouTube
│   │   ├── vk.py                 # Аналитика VK
│   │   ├── tiktok.py             # Аналитика TikTok
│   │   ├── instagram.py          # Аналитика Instagram
│   │   ├── dzen.py               # Аналитика Дзен
│   │   ├── wibes.py              # Аналитика Wibes
│   │   └── pinterest.py          # Аналитика Pinterest
│   ├── components/               # Компоненты UI
│   │   ├── filters.py            # Фильтры дат
│   │   ├── kpi_cards.py          # KPI карточки
│   │   ├── charts.py             # Графики
│   │   ├── tables.py             # Таблицы
│   │   └── video_table.py        # Таблица видео
│   ├── services/                 # Сервисы dashboard
│   │   ├── api_client.py         # HTTP клиент к API
│   │   ├── cache_manager.py      # Кэширование
│   │   └── data_processor.py     # Обработка данных
│   └── utils/                    # Утилиты
│       ├── constants.py          # Константы
│       ├── formatters.py         # Форматирование
│       └── session_state.py      # State management
│
├── migrations/                   # Alembic миграции
│   ├── env.py                    # Конфигурация Alembic
│   └── versions/                 # Файлы миграций
│
├── scripts/                      # Вспомогательные скрипты
│   ├── test_*.py                 # Тестовые скрипты
│   └── manual_*.py               # Ручные операции
│
├── tests/                        # Тесты
│   ├── test_parsers/             # Тесты парсеров
│   ├── test_api/                 # Тесты API
│   └── conftest.py               # Pytest конфигурация
│
├── docker-compose.yml            # Development compose
├── docker-compose.prod.yml       # Production compose
├── Dockerfile                    # Образ приложения
├── Dockerfile.prod               # Production образ
├── nginx.conf                    # Nginx конфигурация
├── alembic.ini                   # Alembic конфигурация
├── pyproject.toml                # Python зависимости
├── .env.example                  # Пример переменных окружения
└── README.md                     # Этот файл
```

---

## 🚀 Установка и запуск

### Требования

- Python 3.10+
- PostgreSQL 16+
- Docker + Docker Compose (опционально)

### 1. Клонирование репозитория

```bash
git clone <repository_url>
cd dashboard_v2
```

### 2. Настройка окружения

```bash
# Создать .env файл
cp .env.example .env

# Отредактировать .env и добавить реальные ключи API
nano .env
```

### 3. Запуск через Docker Compose (рекомендуется)

```bash
# Development
docker-compose up -d

# Production
docker-compose -f docker-compose.prod.yml up -d
```

Сервисы будут доступны:
- FastAPI: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Dashboard: http://localhost:8501

### 4. Запуск без Docker (локально)

```bash
# Установить зависимости
pip install -e .

# Создать БД
createdb social_analytics

# Применить миграции
alembic upgrade head

# Запустить FastAPI
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

# В другом терминале запустить Dashboard
streamlit run dashboard/app.py --server.port 8501
```

---

## ⚙️ Конфигурация

### Переменные окружения (.env)

#### База данных
```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/social_analytics
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=social_analytics
```

#### YouTube API
```env
YOUTUBE_API_KEY=AIza...
```

Получить: https://console.cloud.google.com/apis/credentials

#### VK API
```env
VK_ACCESS_TOKEN=vk1.a...
```

Получить: https://dev.vk.com/ru/api/access-token/getting-started

#### Telegram API
```env
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=abc123...
```

Получить: https://my.telegram.org/apps

#### TikTok Display API (OAuth)
```env
TIKTOK_CLIENT_KEY=your_client_key
TIKTOK_CLIENT_SECRET=your_secret
TIKTOK_REDIRECT_URI=http://localhost:8000/api/v1/oauth/tiktok/callback
```

Зарегистрировать приложение: https://developers.tiktok.com/

#### Instagram Graph API (OAuth)
```env
FACEBOOK_APP_ID=123456789
FACEBOOK_APP_SECRET=abc123...
INSTAGRAM_REDIRECT_URI=http://localhost:8000/api/v1/oauth/instagram/callback
FACEBOOK_GRAPH_API_VERSION=v21.0
```

Зарегистрировать приложение: https://developers.facebook.com/

#### Pinterest API (OAuth)
```env
PINTEREST_APP_ID=your_app_id
PINTEREST_APP_SECRET=your_secret
PINTEREST_REDIRECT_URI=http://localhost:8000/api/v1/oauth/pinterest/callback
```

Зарегистрировать приложение: https://developers.pinterest.com/

#### Безопасность
```env
TOKEN_ENCRYPTION_KEY=your_fernet_key_here
```

Сгенерировать ключ:
```python
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
```

#### Scheduler
```env
COLLECT_INTERVAL_HOURS=6
```

#### Другие настройки
```env
LOG_LEVEL=INFO
ENVIRONMENT=production
API_HOST=0.0.0.0
API_PORT=8000
DASHBOARD_PORT=8501
PLAYWRIGHT_HEADLESS=true
PLAYWRIGHT_TIMEOUT=30000
```

---

## 📖 API документация

### Интерактивная документация

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Основные эндпоинты

#### Accounts (Аккаунты)

```http
GET    /api/v1/accounts                  # Список всех аккаунтов
GET    /api/v1/accounts/{id}             # Получить аккаунт
POST   /api/v1/accounts                  # Создать аккаунт
PUT    /api/v1/accounts/{id}             # Обновить аккаунт
DELETE /api/v1/accounts/{id}             # Удалить аккаунт
POST   /api/v1/accounts/{id}/toggle      # Включить/выключить сбор
```

Пример создания аккаунта:
```json
{
  "platform": "telegram",
  "username": "niginart",
  "display_name": "NIGINart Official",
  "is_active": true
}
```

#### Metrics (Метрики)

```http
GET /api/v1/metrics
  ?platform=telegram
  &account_id=1
  &start_date=2024-01-01
  &end_date=2024-01-31
  &limit=100
  &offset=0
```

Ответ:
```json
{
  "total": 248,
  "items": [
    {
      "id": 1,
      "account_id": 1,
      "platform": "telegram",
      "followers_count": 125000,
      "engagement_rate": 4.5,
      "views_count": 50000,
      "likes_count": 2250,
      "collected_at": "2024-01-20T10:00:00Z"
    }
  ]
}
```

#### OAuth (Авторизация платформ)

```http
GET  /api/v1/oauth/{platform}/authorize  # Начать OAuth flow
GET  /api/v1/oauth/{platform}/callback   # Callback после авторизации
POST /api/v1/oauth/{platform}/refresh    # Обновить токен
```

Поддерживаемые платформы: `tiktok`, `instagram`, `pinterest`

#### Health (Мониторинг)

```http
GET /health                               # Статус приложения
```

---

## 🗄️ База данных

### Схема БД

#### Таблица: accounts
```sql
CREATE TABLE accounts (
    id SERIAL PRIMARY KEY,
    platform VARCHAR(50) NOT NULL,
    username VARCHAR(255) NOT NULL,
    display_name VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    advertiser_id VARCHAR(255),  -- Для TikTok
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(platform, username)
);
```

#### Таблица: metrics
```sql
CREATE TABLE metrics (
    id SERIAL PRIMARY KEY,
    account_id INTEGER REFERENCES accounts(id) ON DELETE CASCADE,
    platform VARCHAR(50) NOT NULL,
    followers_count INTEGER,
    engagement_rate FLOAT,
    views_count INTEGER,
    likes_count INTEGER,
    comments_count INTEGER,
    shares_count INTEGER,
    collected_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT idx_metrics_platform_time
        INDEX (platform, collected_at DESC),
    CONSTRAINT idx_metrics_account_time
        INDEX (account_id, collected_at DESC)
);
```

#### Таблица: oauth_credentials
```sql
CREATE TABLE oauth_credentials (
    id SERIAL PRIMARY KEY,
    account_id INTEGER REFERENCES accounts(id) ON DELETE CASCADE,
    platform VARCHAR(50) NOT NULL,
    access_token_encrypted TEXT NOT NULL,
    refresh_token_encrypted TEXT,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(account_id, platform)
);
```

#### Таблица: collection_logs
```sql
CREATE TABLE collection_logs (
    id SERIAL PRIMARY KEY,
    platform VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,  -- success, error, partial
    metrics_collected INTEGER DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    INDEX (platform, completed_at DESC)
);
```

### Миграции

```bash
# Создать новую миграцию
alembic revision --autogenerate -m "описание изменений"

# Применить миграции
alembic upgrade head

# Откатить одну миграцию
alembic downgrade -1

# Показать текущую версию
alembic current

# История миграций
alembic history
```

---

## 🔌 Парсеры платформ

### Архитектура парсеров

Все парсеры наследуются от `BaseParser` и реализуют методы:

```python
class BaseParser:
    async def collect_account_metrics(self, account: Account) -> Optional[Metric]
    async def collect_all_metrics(self) -> List[Metric]
```

### Telegram (Telethon)

**Файл:** `src/parsers/telegram.py`

**Метрики:**
- Количество подписчиков
- Просмотры последних постов
- Реакции (лайки)
- Комментарии
- Пересылки

**Особенности:**
- Требует первичной авторизации через телефон
- Создает `telegram_session.session` файл
- Работает через официальный Telegram Client API

### YouTube (YouTube Data API v3)

**Файл:** `src/parsers/youtube.py`

**Метрики:**
- Подписчики канала
- Просмотры видео
- Лайки/дизлайки
- Комментарии
- Детальная статистика последних видео

**Лимиты:**
- 10,000 quota units/день (бесплатно)
- Оптимизация: батчинг запросов, кэширование

### VK (VK API)

**Файл:** `src/parsers/vk.py`

**Метрики:**
- Подписчики группы
- Просмотры постов
- Лайки
- Комментарии
- Репосты

**Особенности:**
- Использует Service Token (не требует OAuth)
- Поддержка как групп, так и пользователей

### TikTok (Display API + OAuth)

**Файл:** `src/parsers/tiktok.py`

**Метрики:**
- Подписчики
- Лайки
- Комментарии
- Просмотры
- Shares
- Engagement Rate

**OAuth Flow:**
1. Пользователь переходит на `/api/v1/oauth/tiktok/authorize`
2. Авторизуется на TikTok
3. Redirect на callback с кодом
4. Сервер обменивает код на токены
5. Токены шифруются и сохраняются в БД

### Instagram (Graph API + OAuth)

**Файл:** `src/parsers/instagram.py`

**Метрики:**
- Подписчики
- Engagement Rate
- Impressions (показы)
- Reach (охват)
- Stories метрики (если включено)

**OAuth Flow:** аналогично TikTok

**Stories:**
- Опциональный сбор метрик stories
- Включается через `INSTAGRAM_STORIES_COLLECTION_ENABLED=true`
- Оптимизация: batch запросы, индексы БД

### Дзен (Web Scraping)

**Файл:** `src/parsers/dzen.py`

**Метрики:**
- Подписчики
- Просмотры статей
- Лайки

**Технология:**
- Playwright (headless browser)
- Обход защиты от ботов
- Rate limiting: `DZEN_REQUEST_DELAY=2.0`

### Wibes (Web Scraping)

**Файл:** `src/parsers/wibes.py`

**Метрики:**
- Подписчики
- Просмотры
- Лайки

**Технология:** аналогично Дзен

### Pinterest (Web Scraping / будущее API)

**Файл:** `src/parsers/pinterest.py`

**Метрики:**
- Подписчики
- Сохранения (saves)
- Impressions

---

## 📊 Dashboard

### Структура страниц

#### Главная страница (`app.py`)
- Общий обзор всех платформ
- KPI карточки (аккаунты, вовлеченность, подписчики)
- Сравнительные графики
- Логи последних сборов

#### Страницы платформ (`pages/*.py`)
- Фильтры по датам
- KPI метрики платформы
- Графики динамики (временные ряды)
- Таблицы с детальными данными
- Экспорт в Excel

### Компоненты

**Фильтры (`components/filters.py`):**
```python
start_date, end_date = render_date_range_filter()
```

**KPI карточки (`components/kpi_cards.py`):**
```python
render_kpi_card("Подписчики", 125000, delta="+5%", format_type='compact')
```

**Графики (`components/charts.py`):**
```python
chart = ChartBuilder.line_chart(df, x='date', y='followers', title='Рост')
st.plotly_chart(chart, use_container_width=True)
```

### Кэширование

Dashboard использует `@st.cache_data` для оптимизации:

```python
@st.cache_data(ttl=300)  # 5 минут
def fetch_metrics_cached(platform: str, start_date, end_date):
    return api_client.get_metrics(platform, start_date, end_date)
```

---

## 🧪 Разработка

### Установка dev зависимостей

```bash
pip install -e ".[dev]"
```

### Запуск тестов

```bash
# Все тесты
pytest

# С покрытием
pytest --cov=src --cov-report=html

# Только парсеры
pytest tests/test_parsers/

# Конкретный тест
pytest tests/test_api/test_accounts.py::test_create_account
```

### Линтинг и форматирование

```bash
# Ruff (линтер + форматтер)
ruff check src/ dashboard/
ruff format src/ dashboard/

# MyPy (проверка типов)
mypy src/
```

### Структура тестов

```
tests/
├── conftest.py              # Fixtures
├── test_parsers/
│   ├── test_telegram.py
│   ├── test_youtube.py
│   └── test_tiktok.py
├── test_api/
│   ├── test_accounts.py
│   ├── test_metrics.py
│   └── test_oauth.py
└── test_services/
    └── test_metric_service.py
```

### Добавление нового парсера

1. Создать файл `src/parsers/new_platform.py`:
```python
from src.parsers.base import BaseParser
from src.models.metric import Metric

class NewPlatformParser(BaseParser):
    def __init__(self, api_key: str):
        super().__init__("new_platform")
        self.api_key = api_key

    async def collect_account_metrics(self, account) -> Optional[Metric]:
        # Реализовать логику сбора
        pass
```

2. Зарегистрировать в `src/scheduler/tasks.py`:
```python
from src.parsers.new_platform import NewPlatformParser

async def collect_new_platform_metrics():
    parser = NewPlatformParser(settings.NEW_PLATFORM_API_KEY)
    await parser.collect_all_metrics()
```

3. Добавить в scheduler (`src/scheduler/scheduler.py`):
```python
scheduler.add_job(
    collect_new_platform_metrics,
    trigger=IntervalTrigger(hours=settings.COLLECT_INTERVAL_HOURS),
    id="new_platform_metrics_collection"
)
```

4. Создать миграцию для новых полей (если нужно):
```bash
alembic revision --autogenerate -m "add new_platform support"
alembic upgrade head
```

5. Добавить страницу dashboard: `dashboard/pages/new_platform.py`

---

## 🚢 Деплой

### Production через Docker Compose

```bash
# 1. Подготовить .env для production
cp .env.example .env
nano .env  # Заполнить реальные ключи

# 2. Собрать и запустить
docker-compose -f docker-compose.prod.yml up -d --build

# 3. Применить миграции
docker-compose -f docker-compose.prod.yml exec app alembic upgrade head

# 4. Проверить логи
docker-compose -f docker-compose.prod.yml logs -f
```

### Nginx Reverse Proxy

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

### Переменные окружения для production

```env
ENVIRONMENT=production
LOG_LEVEL=WARNING
DATABASE_URL=postgresql+asyncpg://user:pass@prod-db:5432/social_analytics

# Использовать внешние URLs для OAuth callbacks
TIKTOK_REDIRECT_URI=https://yourdomain.com/api/v1/oauth/tiktok/callback
INSTAGRAM_REDIRECT_URI=https://yourdomain.com/api/v1/oauth/instagram/callback
```

### Мониторинг

**Healthcheck:**
```bash
curl http://localhost:8000/health
```

Ответ:
```json
{
  "status": "healthy",
  "database": "connected",
  "timestamp": "2024-01-20T10:00:00Z"
}
```

**Логи:**
```bash
# FastAPI logs
docker-compose logs -f app

# Dashboard logs
docker-compose logs -f dashboard

# Database logs
docker-compose logs -f db
```

### Backup базы данных

```bash
# Создать backup
docker-compose exec db pg_dump -U postgres social_analytics > backup.sql

# Восстановить backup
docker-compose exec -T db psql -U postgres social_analytics < backup.sql
```

### Безопасность

1. **Шифрование токенов:** Все OAuth токены шифруются через Fernet
2. **Environment variables:** Не коммитить .env в git
3. **HTTPS:** Использовать SSL сертификаты в production
4. **Rate limiting:** Настроить в Nginx или через FastAPI middleware
5. **CORS:** Настроить allowed origins в `src/main.py`

---

## 🔧 Troubleshooting

### Проблема: Database connection failed

**Решение:**
```bash
# Проверить, что PostgreSQL запущен
docker-compose ps db

# Проверить логи
docker-compose logs db

# Пересоздать контейнер
docker-compose down
docker-compose up -d db
```

### Проблема: Telegram авторизация не работает

**Решение:**
```bash
# Удалить старую сессию
rm telegram_session.session

# Запустить интерактивную авторизацию
python scripts/telegram_auth.py
```

### Проблема: YouTube quota exceeded

**Решение:**
- Увеличить `COLLECT_INTERVAL_HOURS`
- Оптимизировать количество запросов
- Использовать quotaUser parameter для распределения квоты

### Проблема: Playwright не запускается

**Решение:**
```bash
# Установить браузеры
playwright install chromium

# В Docker
docker-compose exec app playwright install chromium
```

---

## 📝 Changelog

### v1.0.0 (2024-01-20)
- Поддержка 8 платформ
- OAuth для TikTok, Instagram, Pinterest
- Streamlit Dashboard с интерактивными графиками
- Автоматический сбор метрик по расписанию
- Export в Excel
- Docker Compose для быстрого запуска

---

## 📄 Лицензия

MIT License

---

## 👥 Контакты

Для вопросов по проекту:
- GitHub Issues: [создать issue](https://github.com/yourusername/dashboard_v2/issues)
- Email: support@niginart.com

---

## 🎯 TODO / Roadmap

- [ ] Добавить Telegram Bot для уведомлений
- [ ] Реализовать алерты при падении метрик
- [ ] Добавить A/B тестирование контента
- [ ] ML модели для прогнозирования engagement
- [ ] Поддержка нескольких брендов (multi-tenancy)
- [ ] Mobile приложение (React Native)
