# Social Analytics Dashboard - NIGINart Brand

Automated social media analytics dashboard for tracking NIGINart brand presence across 10 social media platforms.

## Features

- **Automated Data Collection**: Scheduled data collection every 6 hours
- **Multi-Platform Support**: Instagram (3), Telegram, YouTube, VK, TikTok, Pinterest, Яндекс Дзен, Wibes
- **REST API**: FastAPI-based API for data access
- **Interactive Dashboard**: Streamlit-based visualization (Phase 6)
- **Historical Data**: PostgreSQL database with full metrics history

## Tech Stack

- **Backend**: FastAPI + Python 3.10+
- **Database**: PostgreSQL 16
- **Dashboard**: Streamlit
- **Scheduler**: APScheduler
- **ORM**: SQLAlchemy 2.0 (async)
- **Migrations**: Alembic
- **Containerization**: Docker + Docker Compose

## Project Status

**Current Phase**: Phase 1 - Infrastructure ✅
**Completed**:
- ✅ Project structure
- ✅ Docker configuration
- ✅ Database models
- ✅ Alembic migrations
- ✅ Basic FastAPI app
- ✅ Configuration management

**Next Phase**: Phase 2 - Simple Platform Parsers (Telegram, YouTube, VK)

## Prerequisites

- Python 3.10+
- Docker & Docker Compose
- PostgreSQL 16 (or use Docker)

## Quick Start

### 1. Clone Repository

```bash
cd dashboard
```

### 2. Create Environment File

```bash
cp .env.example .env
# Edit .env with your configuration
```

### 3. Start with Docker Compose

```bash
docker-compose up -d
```

This will start:
- PostgreSQL on port 5432
- FastAPI API on port 8000
- Streamlit Dashboard on port 8501 (placeholder)

### 4. Run Migrations

```bash
# Inside app container
docker-compose exec app alembic upgrade head
```

### 5. Seed Initial Accounts

```bash
docker-compose exec app python scripts/seed_accounts.py
```

### 6. Verify Installation

Open http://localhost:8000/docs to see API documentation.

## Development Setup

### Local Development (without Docker)

1. **Create Virtual Environment**

```bash
python -m venv .venv
.venv\Scripts\activate  # On Windows
# source .venv/bin/activate  # On Unix
```

2. **Install Dependencies**

```bash
pip install -e .
pip install -e ".[dev]"
```

3. **Setup PostgreSQL**

Make sure PostgreSQL is running and create database:
```bash
createdb social_analytics
```

4. **Run Migrations**

```bash
alembic upgrade head
```

5. **Seed Data**

```bash
python scripts/seed_accounts.py
```

6. **Start API**

```bash
uvicorn src.main:app --reload --port 8000
```

## Platform Setup

### TikTok Setup

TikTok is integrated through **TikTok Display API v2** and optionally **Marketing API v1.3** (for advertising metrics).

#### Prerequisites
- TikTok account (any account type)
- Business Account (optional, only for Marketing API / ads metrics)

#### 1. Register TikTok Application

1. Go to [TikTok for Developers](https://developers.tiktok.com/)
2. Create a new application
3. In application settings:
   - **App Type**: Web
   - **Redirect URI**: `http://localhost:8000/api/v1/oauth/tiktok/callback` (development)
   - **Scopes**: Select the following:
     - `user.info.basic` - Basic user information
     - `user.info.profile` - User profile data
     - `user.info.stats` - Statistics (followers, following, etc.)
     - `video.list` - List of videos
     - `business.info` (optional) - For Marketing API
     - `user.insights` (optional) - For audience insights

4. Copy your **Client Key** and **Client Secret**

#### 2. Configure Environment Variables

Add to your `.env` file:
```bash
# TikTok Display API
TIKTOK_CLIENT_KEY=your_client_key_here
TIKTOK_CLIENT_SECRET=your_client_secret_here
TIKTOK_REDIRECT_URI=http://localhost:8000/api/v1/oauth/tiktok/callback

# Token encryption (if not already set)
TOKEN_ENCRYPTION_KEY=your_fernet_key_here
```

**Generate TOKEN_ENCRYPTION_KEY**:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

#### 3. OAuth Authorization

**Development (local)**:
1. Start the application: `docker-compose up -d`
2. Open in browser: `http://localhost:8000/api/v1/oauth/tiktok/start`
3. Authorize through TikTok OAuth
4. After redirect, the account will be created/updated in database

**Production (HTTPS required)**:
- TikTok requires HTTPS for production redirect URI
- Update `TIKTOK_REDIRECT_URI=https://yourdomain.com/api/v1/oauth/tiktok/callback`
- Ensure URI is added to TikTok App settings in Developer Portal

#### 4. Verify Integration

```bash
# Check TikTok accounts list
curl http://localhost:8000/api/v1/tiktok/accounts

# Get metrics for an account
curl http://localhost:8000/api/v1/tiktok/accounts/{account_id}/metrics

# Trigger data collection
curl -X POST http://localhost:8000/api/v1/collect -H "Content-Type: application/json" -d '{"platform": "tiktok"}'

# Open dashboard
# http://localhost:8501 → "🎵 TikTok" page
```

#### 5. Marketing API (Optional)

**For ads metrics, you need a Business Account:**
1. Convert your TikTok account to Business Account: [TikTok Business](https://www.tiktok.com/business/)
2. During OAuth authorization, the system will automatically detect `advertiser_id`
3. If `advertiser_id` is found - `ads_metrics` field will appear in metrics with:
   - `7d`, `30d`, `90d`, `lifetime` - Metrics for different time periods
   - `total_spend`, `total_impressions`, `total_clicks`, `avg_ctr`, `avg_cpm`
   - `audience_insights` - Demographics, interests, and audience data

**Graceful Degradation**: If Business Account is not connected, the system continues working without ads metrics.

#### 6. Content Analytics

TikTok page includes **advanced content analytics** via `TikTokContentAnalyzer`:
- **Hashtag Analysis**: Top hashtags, trends (rising/stable/declining)
- **Posting Patterns**: Best days/hours for posting, optimal frequency
- **Duration Analysis**: Optimal video duration (0-15s, 15-30s, 30-60s, 1-3min, 3min+)
- **Viral Content**: Viral video detection (threshold 1.5-5.0x from average)

**API Endpoint**:
```bash
curl "http://localhost:8000/api/v1/tiktok/accounts/{account_id}/analytics/content?viral_threshold=3.0"
```

**Dashboard**: "🔍 Аналитика контента" tab on TikTok page

#### Troubleshooting

**Q: OAuth redirect returns "invalid_request"?**
- Verify that `TIKTOK_REDIRECT_URI` exactly matches the URI in app settings (including http/https)
- Ensure `TOKEN_ENCRYPTION_KEY` is set in `.env`

**Q: No ads_metrics in API response?**
- This is normal if the account is not a Business Account
- Check database: `SELECT advertiser_id FROM accounts WHERE platform='tiktok'`
- If `advertiser_id IS NULL` - connect Business Account

**Q: Content analytics returns success=false?**
- Insufficient videos for analysis (minimum 3-8 depending on analysis type)
- Verify `recent_videos` in `extra_data`: `curl .../metrics | jq '.recent_videos | length'`

**Q: Rate limiting errors?**
- TikTok Display API: Monitor limits in Developer Dashboard
- TikTok Marketing API: 10 requests/second (automatically controlled via semaphore)

## Project Structure

```
dashboard/
├── src/                      # Source code
│   ├── api/                  # FastAPI routes
│   ├── config/               # Configuration
│   ├── db/                   # Database layer
│   ├── models/               # SQLAlchemy models
│   ├── parsers/              # Platform parsers
│   ├── services/             # Business logic (Phase 4)
│   └── scheduler/            # APScheduler jobs (Phase 4)
├── dashboard/                # Streamlit app (Phase 6)
├── tests/                    # Tests
├── migrations/               # Alembic migrations
├── scripts/                  # Utility scripts
├── docker-compose.yml        # Docker orchestration
├── Dockerfile                # Container image
├── pyproject.toml            # Dependencies
└── alembic.ini              # Migration config
```

## API Endpoints (Phase 1)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | API information |
| GET | `/api/v1/health` | Health check |

## Database Schema

### Tables

- **accounts**: Social media accounts configuration
- **metrics**: Historical metrics data
- **collection_logs**: Data collection audit log

See `tech.md` for detailed schema documentation.

## Running Tests

```bash
pytest tests/ -v --cov=src
```

## Linting & Type Checking

```bash
# Linting
ruff check src/

# Type checking
mypy src/

# Format code
ruff format src/
```

## Environment Variables

See `.env.example` for all available configuration options.

Key variables:
- `DATABASE_URL`: PostgreSQL connection string
- `YOUTUBE_API_KEY`: YouTube Data API key
- `VK_ACCESS_TOKEN`: VK API token
- `TELEGRAM_API_ID`: Telegram API credentials
- `COLLECT_INTERVAL_HOURS`: Collection frequency

## Monitoring

- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/v1/health
- **Database**: Connect to localhost:5432

## Troubleshooting

### Database Connection Issues

```bash
# Check PostgreSQL is running
docker-compose ps

# View logs
docker-compose logs db

# Reset database
docker-compose down -v
docker-compose up -d
```

### Migration Issues

```bash
# Check current migration
alembic current

# Create new migration
alembic revision --autogenerate -m "description"

# Rollback one migration
alembic downgrade -1
```

## Development Workflow

1. Make changes to code
2. Run linters: `ruff check src/`
3. Run tests: `pytest`
4. Create migration if models changed: `alembic revision --autogenerate -m "description"`
5. Apply migration: `alembic upgrade head`

## Contributing

1. Follow PEP 8 style guide
2. Add type hints to all functions
3. Write tests for new features
4. Ensure code passes ruff and mypy
5. Update documentation

## License

MIT License

## Support

For issues and questions, please check the technical specification in `tech.md`.

---

**Phase 1 Complete!** 🎉

Next: Implement parsers for Telegram, YouTube, and VK platforms.
