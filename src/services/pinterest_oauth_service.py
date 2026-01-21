from datetime import datetime, timedelta
from typing import Optional, Dict
from uuid import uuid4
import logging
import base64
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.config.settings import get_settings
from src.models.oauth_state import OAuthState
from src.db.repository import BaseRepository
logger = logging.getLogger(__name__)
settings = get_settings()
class PinterestOAuthService:
    AUTHORIZE_URL = "https://www.pinterest.com/oauth/"
    TOKEN_URL = "https://api.pinterest.com/v5/oauth/token"
    API_BASE_URL = "https://api.pinterest.com/v5"
    DEFAULT_SCOPES = [
        "user_accounts:read",
        "pins:read",
        "boards:read",
    ]
    def __init__(self, db: Optional[AsyncSession] = None):
        self.db = db
        if db:
            self.state_repo = BaseRepository(OAuthState, db)
    async def generate_auth_url(
        self, user_identifier: Optional[str] = None, scopes: Optional[list[str]] = None
    ) -> tuple[str, str]:
        if not self.db:
            raise RuntimeError("Database session required for state management")
        state = str(uuid4())
        await self.state_repo.create(
            state=state,
            platform="pinterest",
            user_identifier=user_identifier,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(minutes=10),
            is_used=False,
        )
        await self.db.commit()
        scopes_str = ",".join(scopes or self.DEFAULT_SCOPES)
        params = {
            "client_id": settings.pinterest_app_id,
            "redirect_uri": settings.pinterest_redirect_uri,
            "response_type": "code",
            "scope": scopes_str,
            "state": state,
        }
        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        auth_url = f"{self.AUTHORIZE_URL}?{query_string}"
        logger.info(f"Generated Pinterest auth URL with state {state}")
        return auth_url, state
    async def validate_state(self, state: str) -> bool:
        if not self.db:
            raise RuntimeError("Database session required for state validation")
        result = await self.db.execute(
            select(OAuthState).where(OAuthState.state == state)
        )
        oauth_state = result.scalar_one_or_none()
        if not oauth_state:
            logger.warning(f"State {state} not found in database (possible CSRF attack)")
            return False
        if not oauth_state.is_valid:
            logger.warning(
                f"State {state} is invalid "
                f"(expired={oauth_state.is_expired}, used={oauth_state.is_used})"
            )
            return False
        await self.state_repo.update(state, is_used=True)
        await self.db.commit()
        logger.info(f"State {state} validated successfully")
        return True
    def _get_auth_header(self) -> str:
        credentials = f"{settings.pinterest_app_id}:{settings.pinterest_app_secret}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded}"
    async def exchange_code_for_tokens(self, code: str) -> Dict[str, any]:
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": settings.pinterest_redirect_uri,
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.TOKEN_URL,
                data=payload,
                headers={
                    "Authorization": self._get_auth_header(),
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()
            if "access_token" not in data:
                logger.error(f"Invalid Pinterest token response: {data}")
                raise ValueError("Invalid Pinterest token response format")
            logger.info(
                f"Successfully exchanged code for tokens, "
                f"expires_in={data.get('expires_in', 'N/A')}s"
            )
            return {
                "access_token": data["access_token"],
                "refresh_token": data.get("refresh_token"),
                "expires_in": data.get("expires_in", 86400),
                "scope": data.get("scope", ""),
                "token_type": data.get("token_type", "bearer"),
            }
    async def refresh_access_token(self, refresh_token: str) -> Dict[str, any]:
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.TOKEN_URL,
                data=payload,
                headers={
                    "Authorization": self._get_auth_header(),
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()
            if "access_token" not in data:
                logger.error(f"Invalid Pinterest refresh response: {data}")
                raise ValueError("Invalid Pinterest refresh response format")
            logger.info("Successfully refreshed Pinterest access token")
            return {
                "access_token": data["access_token"],
                "refresh_token": data.get("refresh_token", refresh_token),
                "expires_in": data.get("expires_in", 86400),
                "scope": data.get("scope", ""),
            }
    async def fetch_user_info(self, access_token: str) -> Dict:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.API_BASE_URL}/user_account",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()
            logger.info(f"Fetched Pinterest user info for {data.get('username')}")
            return data
