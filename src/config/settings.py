from functools import lru_cache
from typing import Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/social_analytics",
        description="PostgreSQL connection string",
    )
    youtube_api_key: str = Field(
        default="mock_youtube_key",
        description="YouTube Data API v3 key",
    )
    vk_access_token: str = Field(
        default="mock_vk_token",
        description="VK API access token",
    )
    telegram_api_id: int = Field(
        default=12345678,
        description="Telegram API ID",
    )
    telegram_api_hash: str = Field(
        default="mock_telegram_hash",
        description="Telegram API hash",
    )
    telegram_bot_token: Optional[str] = Field(
        default=None,
        description="Telegram Bot token (alternative to user session). Get from @BotFather",
    )
    collect_interval_hours: int = Field(
        default=6,
        description="Data collection interval in hours",
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level",
    )
    environment: str = Field(
        default="development",
        description="Environment name",
    )
    api_host: str = Field(
        default="0.0.0.0",
        description="API host",
    )
    api_port: int = Field(
        default=8000,
        description="API port",
    )
    proxy_url: Optional[str] = Field(
        default=None,
        description="Proxy URL for web scraping",
    )
    telegram_session_file: str = Field(
        default="telegram_session",
        description="Telegram session file path (without .session extension)",
    )
    tiktok_client_key: str = Field(
        default="mock_tiktok_client_key",
        description="TikTok Display API Client Key",
    )
    tiktok_client_secret: str = Field(
        default="mock_tiktok_client_secret",
        description="TikTok Display API Client Secret",
    )
    tiktok_redirect_uri: str = Field(
        default="http://localhost:8000/api/v1/oauth/tiktok/callback",
        description="TikTok OAuth redirect URI (must match app settings)",
    )
    facebook_app_id: str = Field(
        default="mock_facebook_app_id",
        description="Facebook App ID for Instagram Graph API",
    )
    facebook_app_secret: str = Field(
        default="mock_facebook_app_secret",
        description="Facebook App Secret",
    )
    instagram_redirect_uri: str = Field(
        default="http://localhost:8000/api/v1/oauth/instagram/callback",
        description="Instagram/Facebook OAuth redirect URI (must match app settings)",
    )
    instagram_system_user_token: Optional[str] = Field(
        default=None,
        description="Instagram System User Token (production only, бессрочный)",
    )
    facebook_graph_api_version: str = Field(
        default="v21.0",
        description="Facebook Graph API version",
    )
    pinterest_app_id: str = Field(
        default="",
        description="Pinterest App ID (from developers.pinterest.com)",
    )
    pinterest_app_secret: str = Field(
        default="",
        description="Pinterest App Secret",
    )
    pinterest_redirect_uri: str = Field(
        default="http://localhost:8000/api/v1/oauth/pinterest/callback",
        description="Pinterest OAuth redirect URI (must match app settings)",
    )
    instagram_stories_collection_enabled: bool = Field(
        default=True,
        description="Enable hourly Instagram Stories collection (default: True)",
    )
    token_encryption_key: str = Field(
        default="",
        description="Fernet encryption key for OAuth tokens (32 url-safe base64-encoded bytes)",
    )
    parser_retry_attempts: int = Field(
        default=3,
        description="Number of retry attempts for failed API calls",
    )
    parser_retry_delay: float = Field(
        default=1.0,
        description="Initial retry delay in seconds (exponential backoff)",
    )
    api_timeout_seconds: int = Field(
        default=30,
        description="Timeout for API requests in seconds",
    )
    playwright_headless: bool = Field(
        default=True,
        description="Run Playwright browser in headless mode",
    )
    playwright_timeout: int = Field(
        default=30000,
        description="Playwright page load timeout in milliseconds",
    )
    dzen_request_delay: float = Field(
        default=2.0,
        description="Delay between Dzen requests to avoid rate limiting (seconds)",
    )
    wibes_request_delay: float = Field(
        default=3.0,
        description="Delay between Wibes requests to avoid bot detection (seconds)",
    )
    dashboard_url: str = Field(
        default="http://localhost:8501",
        description="Dashboard base URL for OAuth redirects",
    )
    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v = v.upper()
        if v not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")
        return v
    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        valid_envs = ["development", "staging", "production"]
        v = v.lower()
        if v not in valid_envs:
            raise ValueError(f"environment must be one of {valid_envs}")
        return v
    @field_validator("token_encryption_key")
    @classmethod
    def validate_encryption_key(cls, v: str) -> str:
        import logging
        logger = logging.getLogger(__name__)
        if not v:
            from cryptography.fernet import Fernet
            logger.warning(
                "TOKEN_ENCRYPTION_KEY not set, generating temporary key. "
                "This is ONLY for development! In production, set a permanent key."
            )
            return Fernet.generate_key().decode()
        try:
            from cryptography.fernet import Fernet
            Fernet(v.encode())
        except Exception as e:
            raise ValueError(
                f"Invalid TOKEN_ENCRYPTION_KEY format: {e}. "
                f"Generate with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
            )
        return v
@lru_cache()
def get_settings() -> Settings:
    return Settings()
