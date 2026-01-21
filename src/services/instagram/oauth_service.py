import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from uuid import uuid4
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.config.settings import get_settings
from src.models.oauth_state import OAuthState
from src.services.instagram.schemas import FacebookPage, FacebookTokenResponse
logger = logging.getLogger(__name__)
settings = get_settings()
class InstagramOAuthService:
    AUTHORIZE_URL = f"https://www.facebook.com/{ version} /dialog/oauth"
    TOKEN_URL = f"https://graph.facebook.com/{ version} /oauth/access_token"
    GRAPH_API_BASE = f"https://graph.facebook.com/{ version} "
    DEFAULT_SCOPES = [
        "pages_show_list",
        "instagram_basic",
        "instagram_manage_insights",
        "pages_read_engagement",
        "business_management",
    ]
    def __init__(self, db: Optional[AsyncSession] = None):
        self.db = db
        self._http_client: Optional[httpx.AsyncClient] = None
    async def generate_auth_url(
        self, user_identifier: Optional[str] = None
    ) -> Tuple[str, str]:
        if not self.db:
            raise RuntimeError("Database session required for state token generation")
        state = str(uuid4())
        oauth_state = OAuthState(
            state=state,
            platform="instagram",
            user_identifier=user_identifier,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(minutes=10),
            is_used=False,
        )
        self.db.add(oauth_state)
        await self.db.commit()
        logger.info(f"Generated OAuth state token for Instagram: {state}")
        auth_url = self.AUTHORIZE_URL.format(version=settings.facebook_graph_api_version)
        params = {
            "client_id": settings.facebook_app_id,
            "redirect_uri": settings.instagram_redirect_uri,
            "state": state,
            "response_type": "code",
            "scope": ",".join(self.DEFAULT_SCOPES),
        }
        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        full_url = f"{auth_url}?{query_string}"
        return full_url, state
    async def validate_state(self, state: str) -> bool:
        if not self.db:
            raise RuntimeError("Database session required for state validation")
        result = await self.db.execute(
            select(OAuthState).where(OAuthState.state == state)
        )
        oauth_state = result.scalar_one_or_none()
        if not oauth_state:
            logger.warning(f"Invalid OAuth state: {state} (not found in database)")
            return False
        if oauth_state.is_expired:
            logger.warning(f"OAuth state expired: {state}")
            return False
        if oauth_state.is_used:
            logger.warning(f"OAuth state already used: {state}")
            return False
        oauth_state.is_used = True
        await self.db.commit()
        logger.info(f"OAuth state validated: {state}")
        return True
    async def exchange_code_for_token(self, code: str) -> Dict:
        client = await self._get_http_client()
        token_url = self.TOKEN_URL.format(version=settings.facebook_graph_api_version)
        logger.info("Exchanging authorization code for short-lived token")
        response = await client.post(
            token_url,
            params={
                "client_id": settings.facebook_app_id,
                "client_secret": settings.facebook_app_secret,
                "redirect_uri": settings.instagram_redirect_uri,
                "code": code,
            },
        )
        response.raise_for_status()
        data = response.json()
        logger.info(
            f"Received short-lived token (expires in {data.get('expires_in', 'N/A')} seconds)"
        )
        return data
    async def exchange_for_long_lived_token(self, short_lived_token: str) -> Dict:
        client = await self._get_http_client()
        token_url = self.TOKEN_URL.format(version=settings.facebook_graph_api_version)
        logger.info("Exchanging short-lived token for long-lived token")
        response = await client.get(
            token_url,
            params={
                "grant_type": "fb_exchange_token",
                "client_id": settings.facebook_app_id,
                "client_secret": settings.facebook_app_secret,
                "fb_exchange_token": short_lived_token,
            },
        )
        response.raise_for_status()
        data = response.json()
        expires_in = data.get("expires_in", 0)
        expires_days = expires_in / 86400 if expires_in > 0 else 0
        logger.info(
            f"Received long-lived token (expires in {expires_days:.1f} days)"
        )
        return data
    async def get_user_pages(self, access_token: str) -> List[FacebookPage]:
        client = await self._get_http_client()
        base_url = self.GRAPH_API_BASE.format(
            version=settings.facebook_graph_api_version
        )
        logger.info("Fetching user's Facebook Pages")
        response = await client.get(
            f"{base_url}/me/accounts",
            params={
                "fields": "id,name,access_token,category,instagram_business_account",
                "access_token": access_token,
            },
        )
        response.raise_for_status()
        data = response.json()
        pages_data = data.get("data", [])
        pages = [FacebookPage(**page) for page in pages_data]
        instagram_pages = [p for p in pages if p.instagram_business_account]
        logger.info(
            f"Found {len(pages)} Facebook Pages, "
            f"{len(instagram_pages)} with Instagram Business Account"
        )
        return instagram_pages
    async def get_instagram_business_account(
        self, page_id: str, page_access_token: str
    ) -> Optional[str]:
        client = await self._get_http_client()
        base_url = self.GRAPH_API_BASE.format(
            version=settings.facebook_graph_api_version
        )
        logger.info(f"Checking Instagram Business Account for Page: {page_id}")
        response = await client.get(
            f"{base_url}/{page_id}",
            params={
                "fields": "instagram_business_account",
                "access_token": page_access_token,
            },
        )
        response.raise_for_status()
        data = response.json()
        ig_account = data.get("instagram_business_account")
        if ig_account:
            ig_account_id = ig_account.get("id")
            logger.info(f"Found Instagram Business Account: {ig_account_id}")
            return ig_account_id
        else:
            logger.info(f"No Instagram Business Account linked to Page {page_id}")
            return None
    async def refresh_long_lived_token(self, current_token: str) -> Dict:
        client = await self._get_http_client()
        token_url = self.TOKEN_URL.format(version=settings.facebook_graph_api_version)
        logger.info("Refreshing long-lived token")
        response = await client.get(
            token_url,
            params={
                "grant_type": "fb_exchange_token",
                "client_id": settings.facebook_app_id,
                "client_secret": settings.facebook_app_secret,
                "fb_exchange_token": current_token,
            },
        )
        response.raise_for_status()
        data = response.json()
        logger.info("Successfully refreshed long-lived token")
        return data
    async def _get_http_client(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=True,
            )
        return self._http_client
    async def close(self) -> None:
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
