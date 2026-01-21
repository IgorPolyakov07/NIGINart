from typing import Dict, List
from uuid import UUID
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import httpx
from src.db.database import get_db
from src.db.repository import BaseRepository
from src.models.account import Account
from src.models.schemas import (
    InstagramOAuthStartResponse,
    InstagramUserInfo,
    FacebookPageResponse,
)
from src.services.instagram.oauth_service import InstagramOAuthService
from src.services.instagram.schemas import FacebookPage
from src.services.token_manager import TokenManager
from src.config.settings import get_settings
logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/api/v1/oauth/instagram", tags=["Instagram OAuth"])
async def _fetch_instagram_user_info(
    instagram_account_id: str, page_access_token: str
) -> InstagramUserInfo:
    graph_api_url = f"https://graph.facebook.com/{settings.facebook_graph_api_version}/{instagram_account_id}"
    fields = [
        "id",
        "username",
        "name",
        "profile_picture_url",
        "followers_count",
        "follows_count",
        "media_count",
    ]
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            graph_api_url,
            params={
                "fields": ",".join(fields),
                "access_token": page_access_token,
            },
        )
        response.raise_for_status()
        data = response.json()
        if "id" not in data or "username" not in data:
            logger.error(f"Invalid Instagram user info response: {data}")
            raise ValueError("Invalid Instagram user info response format")
        return InstagramUserInfo(
            instagram_account_id=data["id"],
            username=data["username"],
            name=data.get("name"),
            profile_picture_url=data.get("profile_picture_url"),
            followers_count=data.get("followers_count", 0),
            follows_count=data.get("follows_count", 0),
            media_count=data.get("media_count", 0),
        )
async def _create_or_update_account(
    db: AsyncSession,
    user_info: InstagramUserInfo,
    page_access_token: str,
) -> Account:
    repo = BaseRepository(Account, db)
    query = select(Account).where(
        Account.platform == "instagram",
        Account.account_id == user_info.instagram_account_id,
    )
    result = await db.execute(query)
    existing_account = result.scalar_one_or_none()
    account_url = f"https://www.instagram.com/{user_info.username}/"
    if existing_account:
        updated_account = await repo.update(
            existing_account.id,
            display_name=user_info.name or user_info.username,
            account_url=account_url,
            is_active=True,
        )
        await db.commit()
        logger.info(
            f"Updated existing Instagram account {existing_account.id} (@{user_info.username})"
        )
        return updated_account
    else:
        new_account = await repo.create(
            platform="instagram",
            account_id=user_info.instagram_account_id,
            account_url=account_url,
            display_name=user_info.name or user_info.username,
            is_active=True,
        )
        await db.commit()
        logger.info(f"Created new Instagram account {new_account.id} (@{user_info.username})")
        return new_account
@router.get("/start", response_model=InstagramOAuthStartResponse, status_code=status.HTTP_200_OK)
async def start_instagram_oauth(
    db: AsyncSession = Depends(get_db),
) -> InstagramOAuthStartResponse:
    try:
        oauth_service = InstagramOAuthService(db)
        auth_url, state = await oauth_service.generate_auth_url()
        logger.info(f"Generated Instagram/Facebook OAuth authorization URL with state {state}")
        return InstagramOAuthStartResponse(authorization_url=auth_url, state=state)
    except Exception as e:
        logger.error(f"Failed to start Instagram OAuth flow: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start OAuth flow: {str(e)}",
        )
@router.get("/callback", status_code=status.HTTP_307_TEMPORARY_REDIRECT)
async def instagram_oauth_callback(
    code: str = Query(None, description="Authorization code from Facebook"),
    state: str = Query(None, description="CSRF state token"),
    error: str = Query(None, description="Error code from Facebook"),
    error_reason: str = Query(None, description="Error reason from Facebook"),
    error_description: str = Query(None, description="Error description from Facebook"),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    dashboard_url = "http://localhost:8501"
    instagram_page_url = f"{dashboard_url}/5_%F0%9F%93%B8_Instagram"
    if error:
        error_msg = error_description or error_reason or error
        logger.error(f"Facebook OAuth error: {error} - {error_msg}")
        return RedirectResponse(
            url=f"{dashboard_url}/?oauth_error={error_msg}",
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
        )
    if not code or not state:
        logger.error("Missing required parameters: code or state")
        return RedirectResponse(
            url=f"{dashboard_url}/?oauth_error=missing_parameters",
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
        )
    try:
        oauth_service = InstagramOAuthService(db)
        if not await oauth_service.validate_state(state):
            logger.warning(f"Invalid OAuth state: {state}")
            return RedirectResponse(
                url=f"{dashboard_url}/?oauth_error=invalid_state",
                status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            )
        logger.info("Step 1/3: Exchanging code for short-lived token")
        short_lived_token_data = await oauth_service.exchange_code_for_token(code)
        short_lived_token = short_lived_token_data["access_token"]
        logger.info(
            f"Received short-lived token (expires in {short_lived_token_data.get('expires_in', 'N/A')}s)"
        )
        logger.info("Step 2/3: Exchanging short-lived for long-lived token (CRITICAL!)")
        long_lived_token_data = await oauth_service.exchange_for_long_lived_token(
            short_lived_token
        )
        long_lived_token = long_lived_token_data["access_token"]
        expires_in = long_lived_token_data.get("expires_in", 0)
        expires_days = expires_in / 86400 if expires_in > 0 else 0
        logger.info(f"Received long-lived token (expires in {expires_days:.1f} days)")
        logger.info("Step 3/3: Fetching user's Facebook Pages")
        instagram_pages = await oauth_service.get_user_pages(long_lived_token)
        if not instagram_pages:
            logger.warning("No Facebook Pages with Instagram Business Account found")
            return RedirectResponse(
                url=f"{dashboard_url}/?oauth_error=no_instagram_pages",
                status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            )
        selected_page = instagram_pages[0]
        logger.info(
            f"Auto-selected Facebook Page: {selected_page.name} (ID: {selected_page.id})"
        )
        instagram_account_id = selected_page.instagram_business_account["id"]
        logger.info(f"Instagram Business Account ID: {instagram_account_id}")
        user_info = await _fetch_instagram_user_info(
            instagram_account_id, selected_page.access_token
        )
        logger.info(f"Fetched Instagram user info for @{user_info.username}")
        account = await _create_or_update_account(db, user_info, selected_page.access_token)
        token_manager = TokenManager(db)
        await token_manager.save_tokens(
            account.id,
            selected_page.access_token,
            None,
            expires_in,
            ",".join(InstagramOAuthService.DEFAULT_SCOPES),
        )
        logger.info(f"Saved encrypted Page access token for account {account.id}")
        return RedirectResponse(
            url=f"{instagram_page_url}?oauth_success=true&account_id={account.id}",
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
        )
    except httpx.HTTPStatusError as e:
        logger.error(f"Facebook API error during OAuth callback: {e.response.text}", exc_info=True)
        return RedirectResponse(
            url=f"{dashboard_url}/?oauth_error=facebook_api_error",
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
        )
    except ValueError as e:
        logger.error(f"Invalid response format during OAuth callback: {e}", exc_info=True)
        return RedirectResponse(
            url=f"{dashboard_url}/?oauth_error=invalid_response",
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
        )
    except Exception as e:
        logger.error(f"Unexpected error during OAuth callback: {e}", exc_info=True)
        return RedirectResponse(
            url=f"{dashboard_url}/?oauth_error=unknown",
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
        )
    finally:
        await oauth_service.close()
@router.delete("/{account_id}/revoke", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_instagram_tokens(
    account_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    try:
        repo = BaseRepository(Account, db)
        account = await repo.get(account_id)
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Account with id {account_id} not found",
            )
        if account.platform != "instagram":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Account {account_id} is not an Instagram account (platform={account.platform})",
            )
        await repo.update(
            account_id,
            encrypted_access_token=None,
            encrypted_refresh_token=None,
            token_expires_at=None,
            token_scope=None,
        )
        await db.commit()
        logger.info(f"Successfully revoked tokens for Instagram account {account_id}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to revoke tokens for account {account_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to revoke tokens: {str(e)}",
        )
@router.get("/pages", response_model=List[FacebookPageResponse], status_code=status.HTTP_200_OK)
async def get_facebook_pages(
    access_token: str = Query(..., description="User's Facebook access token"),
    db: AsyncSession = Depends(get_db),
) -> List[FacebookPageResponse]:
    try:
        oauth_service = InstagramOAuthService(db)
        graph_api_url = f"https://graph.facebook.com/{settings.facebook_graph_api_version}/me/accounts"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                graph_api_url,
                params={
                    "fields": "id,name,access_token,category,instagram_business_account",
                    "access_token": access_token,
                },
            )
            response.raise_for_status()
            data = response.json()
            pages_data = data.get("data", [])
            pages_response = []
            for page in pages_data:
                ig_account = page.get("instagram_business_account")
                pages_response.append(
                    FacebookPageResponse(
                        id=page["id"],
                        name=page["name"],
                        category=page.get("category"),
                        has_instagram=ig_account is not None,
                        instagram_account_id=ig_account["id"] if ig_account else None,
                    )
                )
            logger.info(f"Fetched {len(pages_response)} Facebook Pages")
            return pages_response
    except httpx.HTTPStatusError as e:
        logger.error(f"Facebook API error: {e.response.text}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch Facebook Pages: {e.response.text}",
        )
    except Exception as e:
        logger.error(f"Failed to fetch Facebook Pages: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch Facebook Pages: {str(e)}",
        )
    finally:
        await oauth_service.close()
