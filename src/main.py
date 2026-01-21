from contextlib import asynccontextmanager
from datetime import datetime
from typing import AsyncGenerator, Optional
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.dependencies import verify_database_connection
from src.api.routers import collection, accounts, youtube, oauth, instagram, instagram_stories, instagram_analytics, instagram_insights, tiktok, telegram, pinterest
from src.config.settings import get_settings
from src.db.database import get_db
from src.models.schemas import HealthResponse
from src.services.scheduler_service import SchedulerService
settings = get_settings()
scheduler_service: Optional[SchedulerService] = None
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    global scheduler_service
    print("Starting Social Analytics API...")
    print(f"Database: {settings.database_url}")
    print(f"Environment: {settings.environment}")
    try:
        scheduler_service = SchedulerService()
        await scheduler_service.start()
    except Exception as e:
        print(f"WARNING: Scheduler failed to start: {e}")
        print("WARNING: Continuing without automatic collection")
    yield
    print("Shutting down Social Analytics API...")
    if scheduler_service:
        await scheduler_service.stop()
app = FastAPI(
    title="Social Analytics API",
    description="REST API for NIGINart Social Media Analytics Dashboard",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(collection.router)
app.include_router(accounts.router)
app.include_router(youtube.router)
app.include_router(oauth.router)
app.include_router(instagram.router)
app.include_router(instagram_stories.router)
app.include_router(instagram_analytics.router)
app.include_router(instagram_insights.router)
app.include_router(tiktok.router)
app.include_router(telegram.router)
app.include_router(pinterest.router)
@app.get("/api/v1/health", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)) -> HealthResponse:
    db_status = await verify_database_connection(db)
    return HealthResponse(
        status="healthy" if db_status else "unhealthy",
        version="1.0.0",
        database="connected" if db_status else "disconnected",
        timestamp=datetime.utcnow(),
    )
@app.get("/")
async def root() -> dict:
    return {
        "name": "Social Analytics API",
        "version": "1.0.0",
        "description": "NIGINart Social Media Analytics Dashboard",
        "docs": "/docs",
        "health": "/api/v1/health",
    }
