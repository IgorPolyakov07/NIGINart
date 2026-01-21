from datetime import datetime, timedelta
from typing import Optional, Dict
from uuid import uuid4
import logging
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.config.settings import get_settings
from src.models.oauth_state import OAuthState
from src.db.repository import BaseRepository
logger = logging.getLogger(__name__)
settings = get_settings()
class TikTokOAuthService:
    AUTHORIZE_URL = "https://www.tiktok.com/v2/auth/authorize/"
    TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
    REVOKE_URL = "https://open.tiktokapis.com/v2/oauth/revoke/"
    DEFAULT_SCOPES = [
        "user.info.basic",
        "user.info.profile",
        "user.info.stats",
        "video.list",
        "business.info",
        "user.insights",
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
            platform="tiktok",
            user_identifier=user_identifier,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(minutes=10),
            is_used=False,
        )
        await self.db.commit()
        scopes_str = ",".join(scopes or self.DEFAULT_SCOPES)
        params = {
            "client_key": settings.tiktok_client_key,
            "scope": scopes_str,
            "response_type": "code",
            "redirect_uri": settings.tiktok_redirect_uri,
            "state": state,
        }
        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        auth_url = f"{self.AUTHORIZE_URL}?{query_string}"
        logger.info(f"Generated TikTok auth URL with state {state}")
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
    async def exchange_code_for_tokens(self, code: str) -> Dict[str, any]:
        payload = {
            "client_key": settings.tiktok_client_key,
            "client_secret": settings.tiktok_client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": settings.tiktok_redirect_uri,
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.TOKEN_URL,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()
            if "data" not in data or "access_token" not in data["data"]:
                logger.error(f"Invalid TikTok token response: {data}")
                raise ValueError(f"Invalid TikTok token response format")
            token_data = data["data"]
            logger.info(
                f"Successfully exchanged code for tokens, "
                f"expires_in={token_data['expires_in']}s"
            )
            return {
                "access_token": token_data["access_token"],
                "refresh_token": token_data["refresh_token"],
                "expires_in": token_data["expires_in"],
                "scope": token_data.get("scope", ""),
                "open_id": token_data["open_id"],
            }
    async def refresh_access_token(self, refresh_token: str) -> Dict[str, any]:
        payload = {
            "client_key": settings.tiktok_client_key,
            "client_secret": settings.tiktok_client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.TOKEN_URL,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()
            if "data" not in data or "access_token" not in data["data"]:
                logger.error(f"Invalid TikTok refresh response: {data}")
                raise ValueError(f"Invalid TikTok refresh response format")
            token_data = data["data"]
            logger.info("Successfully refreshed access token")
            return {
                "access_token": token_data["access_token"],
                "refresh_token": token_data.get("refresh_token", refresh_token),
                "expires_in": token_data["expires_in"],
                "scope": token_data.get("scope", ""),
            }
    async def revoke_token(self, access_token: str) -> None:
        payload = {
            "client_key": settings.tiktok_client_key,
            "client_secret": settings.tiktok_client_secret,
            "token": access_token,
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.REVOKE_URL,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30.0,
            )
            response.raise_for_status()
            logger.info("Successfully revoked access token on TikTok")
    async def get_advertiser_id(self, access_token: str) -> Optional[str]:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://business-api.tiktok.com/open_api/v1.3/business/get/",
                    headers={"Access-Token": access_token},
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()
                if data.get("code") == 0 and data.get("data"):
                    businesses = data["data"].get("list", [])
                    if businesses:
                        advertiser_id = businesses[0].get("advertiser_id")
                        logger.info(f"Found advertiser_id: {advertiser_id}")
                        return advertiser_id
                logger.info("No Business Account found for user")
                return None
        except Exception as e:
            logger.warning(f"Failed to fetch advertiser_id: {e}")
            return None
