from typing import Dict
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
from src.models.schemas import TikTokOAuthStartResponse, TikTokUserInfo, PinterestOAuthStartResponse
from src.services.tiktok_oauth_service import TikTokOAuthService
from src.services.pinterest_oauth_service import PinterestOAuthService
from src.services.token_manager import TokenManager
from src.config.settings import get_settings
logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/api/v1/oauth", tags=["oauth"])
async def _fetch_tiktok_user_info(access_token: str) -> TikTokUserInfo:
    user_info_url = "https://open.tiktokapis.com/v2/user/info/"
    fields = [
        "open_id",
        "union_id",
        "avatar_url",
        "avatar_url_100",
        "avatar_large_url",
        "display_name",
        "bio_description",
        "profile_deep_link",
        "is_verified",
        "follower_count",
        "following_count",
        "likes_count",
        "video_count",
    ]
    async with httpx.AsyncClient() as client:
        response = await client.get(
            user_info_url,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            params={"fields": ",".join(fields)},
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()
        if "data" not in data or "user" not in data["data"]:
            logger.error(f"Invalid TikTok user info response: {data}")
            raise ValueError("Invalid TikTok user info response format")
        user_data = data["data"]["user"]
        return TikTokUserInfo(
            open_id=user_data["open_id"],
            union_id=user_data.get("union_id"),
            avatar_url=user_data.get("avatar_url"),
            avatar_url_100=user_data.get("avatar_url_100"),
            avatar_large_url=user_data.get("avatar_large_url"),
            display_name=user_data["display_name"],
            bio_description=user_data.get("bio_description"),
            profile_deep_link=user_data.get("profile_deep_link"),
            is_verified=user_data.get("is_verified", False),
            follower_count=user_data.get("follower_count", 0),
            following_count=user_data.get("following_count", 0),
            likes_count=user_data.get("likes_count", 0),
            video_count=user_data.get("video_count", 0),
        )
async def _create_or_update_account(
    db: AsyncSession, token_data: Dict, user_info: TikTokUserInfo
) -> Account:
    repo = BaseRepository(Account, db)
    query = select(Account).where(
        Account.platform == "tiktok",
        Account.account_id == user_info.open_id
    )
    result = await db.execute(query)
    existing_account = result.scalar_one_or_none()
    account_url = user_info.profile_deep_link or f"https://www.tiktok.com/@{user_info.display_name}"
    if existing_account:
        updated_account = await repo.update(
            existing_account.id,
            display_name=user_info.display_name,
            account_url=account_url,
            is_active=True,
        )
        await db.commit()
        logger.info(f"Updated existing TikTok account {existing_account.id} ({user_info.display_name})")
        return updated_account
    else:
        new_account = await repo.create(
            platform="tiktok",
            account_id=user_info.open_id,
            account_url=account_url,
            display_name=user_info.display_name,
            is_active=True,
        )
        await db.commit()
        logger.info(f"Created new TikTok account {new_account.id} ({user_info.display_name})")
        return new_account
@router.get("/tiktok/start", response_model=TikTokOAuthStartResponse, status_code=status.HTTP_200_OK)
async def start_tiktok_oauth(
    db: AsyncSession = Depends(get_db)
) -> TikTokOAuthStartResponse:
    try:
        oauth_service = TikTokOAuthService(db)
        auth_url, state = await oauth_service.generate_auth_url()
        logger.info(f"Generated TikTok OAuth authorization URL with state {state}")
        return TikTokOAuthStartResponse(
            authorization_url=auth_url,
            state=state
        )
    except Exception as e:
        logger.error(f"Failed to start TikTok OAuth flow: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start OAuth flow: {str(e)}"
        )
@router.get("/tiktok/callback", status_code=status.HTTP_307_TEMPORARY_REDIRECT)
async def tiktok_oauth_callback(
    code: str = Query(..., description="Authorization code from TikTok"),
    state: str = Query(..., description="CSRF state token"),
    db: AsyncSession = Depends(get_db)
) -> RedirectResponse:
    try:
        oauth_service = TikTokOAuthService(db)
        if not await oauth_service.validate_state(state):
            logger.warning(f"Invalid OAuth state: {state}")
            return RedirectResponse(
                url=f"{settings.dashboard_url}/?oauth_error=invalid_state",
                status_code=status.HTTP_307_TEMPORARY_REDIRECT
            )
        token_data = await oauth_service.exchange_code_for_tokens(code)
        logger.info(f"Successfully exchanged code for tokens, open_id={token_data['open_id']}")
        user_info = await _fetch_tiktok_user_info(token_data["access_token"])
        logger.info(f"Fetched user info for {user_info.display_name} (@{user_info.open_id})")
        account = await _create_or_update_account(db, token_data, user_info)
        token_manager = TokenManager(db)
        await token_manager.save_tokens(
            account.id,
            token_data["access_token"],
            token_data["refresh_token"],
            token_data["expires_in"],
            token_data["scope"]
        )
        logger.info(f"Saved encrypted tokens for account {account.id}")
        advertiser_id = await oauth_service.get_advertiser_id(token_data["access_token"])
        if advertiser_id:
            account_repo = BaseRepository(Account, db)
            await account_repo.update(
                account.id,
                advertiser_id=advertiser_id
            )
            await db.commit()
            logger.info(f"Saved advertiser_id {advertiser_id} for account {account.display_name}")
        else:
            logger.info(f"No Business Account for {account.display_name}, ads metrics will be skipped")
        tiktok_page = f"{settings.dashboard_url}/4_%F0%9F%8E%B5_TikTok"
        return RedirectResponse(
            url=f"{tiktok_page}?oauth_success=true&account_id={account.id}",
            status_code=status.HTTP_307_TEMPORARY_REDIRECT
        )
    except httpx.HTTPStatusError as e:
        logger.error(f"TikTok API error during OAuth callback: {e.response.text}", exc_info=True)
        return RedirectResponse(
            url=f"{settings.dashboard_url}/?oauth_error=tiktok_api_error",
            status_code=status.HTTP_307_TEMPORARY_REDIRECT
        )
    except ValueError as e:
        logger.error(f"Invalid response format during OAuth callback: {e}", exc_info=True)
        return RedirectResponse(
            url=f"{settings.dashboard_url}/?oauth_error=invalid_response",
            status_code=status.HTTP_307_TEMPORARY_REDIRECT
        )
    except Exception as e:
        logger.error(f"Unexpected error during OAuth callback: {e}", exc_info=True)
        return RedirectResponse(
            url=f"{settings.dashboard_url}/?oauth_error=unknown",
            status_code=status.HTTP_307_TEMPORARY_REDIRECT
        )
@router.delete("/tiktok/{account_id}/revoke", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_tiktok_tokens(
    account_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> None:
    try:
        repo = BaseRepository(Account, db)
        account = await repo.get(account_id)
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Account with id {account_id} not found"
            )
        if account.platform != "tiktok":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Account {account_id} is not a TikTok account (platform={account.platform})"
            )
        token_manager = TokenManager(db)
        await token_manager.revoke_tokens(account_id)
        logger.info(f"Successfully revoked tokens for TikTok account {account_id}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to revoke tokens for account {account_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to revoke tokens: {str(e)}"
        )
async def _create_or_update_pinterest_account(
    db: AsyncSession, token_data: Dict, user_info: Dict
) -> Account:
    repo = BaseRepository(Account, db)
    query = select(Account).where(
        Account.platform == "pinterest",
        Account.account_id == user_info["username"]
    )
    result = await db.execute(query)
    existing_account = result.scalar_one_or_none()
    account_url = f"https://pinterest.com/{user_info['username']}"
    display_name = user_info.get("business_name") or user_info.get("username", "Pinterest User")
    if existing_account:
        updated_account = await repo.update(
            existing_account.id,
            display_name=display_name,
            account_url=account_url,
            is_active=True,
        )
        await db.commit()
        logger.info(f"Updated existing Pinterest account {existing_account.id} ({display_name})")
        return updated_account
    else:
        new_account = await repo.create(
            platform="pinterest",
            account_id=user_info["username"],
            account_url=account_url,
            display_name=display_name,
            is_active=True,
        )
        await db.commit()
        logger.info(f"Created new Pinterest account {new_account.id} ({display_name})")
        return new_account
@router.get("/pinterest/start", response_model=PinterestOAuthStartResponse, status_code=status.HTTP_200_OK)
async def start_pinterest_oauth(
    db: AsyncSession = Depends(get_db)
) -> PinterestOAuthStartResponse:
    try:
        oauth_service = PinterestOAuthService(db)
        auth_url, state = await oauth_service.generate_auth_url()
        logger.info(f"Generated Pinterest OAuth authorization URL with state {state}")
        return PinterestOAuthStartResponse(
            authorization_url=auth_url,
            state=state
        )
    except Exception as e:
        logger.error(f"Failed to start Pinterest OAuth flow: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start OAuth flow: {str(e)}"
        )
@router.get("/pinterest/callback", status_code=status.HTTP_307_TEMPORARY_REDIRECT)
async def pinterest_oauth_callback(
    code: str = Query(..., description="Authorization code from Pinterest"),
    state: str = Query(..., description="CSRF state token"),
    db: AsyncSession = Depends(get_db)
) -> RedirectResponse:
    try:
        oauth_service = PinterestOAuthService(db)
        if not await oauth_service.validate_state(state):
            logger.warning(f"Invalid Pinterest OAuth state: {state}")
            return RedirectResponse(
                url=f"{settings.dashboard_url}/?oauth_error=invalid_state",
                status_code=status.HTTP_307_TEMPORARY_REDIRECT
            )
        token_data = await oauth_service.exchange_code_for_tokens(code)
        logger.info("Successfully exchanged Pinterest code for tokens")
        user_info = await oauth_service.fetch_user_info(token_data["access_token"])
        logger.info(f"Fetched Pinterest user info for {user_info.get('username')}")
        account = await _create_or_update_pinterest_account(db, token_data, user_info)
        token_manager = TokenManager(db)
        await token_manager.save_tokens(
            account.id,
            token_data["access_token"],
            token_data.get("refresh_token"),
            token_data.get("expires_in", 86400),
            token_data.get("scope", "")
        )
        logger.info(f"Saved encrypted tokens for Pinterest account {account.id}")
        pinterest_page = f"{settings.dashboard_url}/8_%F0%9F%93%8C_Pinterest"
        return RedirectResponse(
            url=f"{pinterest_page}?oauth_success=true&account_id={account.id}",
            status_code=status.HTTP_307_TEMPORARY_REDIRECT
        )
    except httpx.HTTPStatusError as e:
        logger.error(f"Pinterest API error during OAuth callback: {e.response.text}", exc_info=True)
        return RedirectResponse(
            url=f"{settings.dashboard_url}/?oauth_error=pinterest_api_error",
            status_code=status.HTTP_307_TEMPORARY_REDIRECT
        )
    except ValueError as e:
        logger.error(f"Invalid response format during Pinterest OAuth callback: {e}", exc_info=True)
        return RedirectResponse(
            url=f"{settings.dashboard_url}/?oauth_error=invalid_response",
            status_code=status.HTTP_307_TEMPORARY_REDIRECT
        )
    except Exception as e:
        logger.error(f"Unexpected error during Pinterest OAuth callback: {e}", exc_info=True)
        return RedirectResponse(
            url=f"{settings.dashboard_url}/?oauth_error=unknown",
            status_code=status.HTTP_307_TEMPORARY_REDIRECT
        )
@router.delete("/pinterest/{account_id}/revoke", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_pinterest_tokens(
    account_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> None:
    try:
        repo = BaseRepository(Account, db)
        account = await repo.get(account_id)
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Account with id {account_id} not found"
            )
        if account.platform != "pinterest":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Account {account_id} is not a Pinterest account (platform={account.platform})"
            )
        token_manager = TokenManager(db)
        await token_manager.revoke_tokens(account_id)
        logger.info(f"Successfully revoked tokens for Pinterest account {account_id}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to revoke tokens for Pinterest account {account_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to revoke tokens: {str(e)}"
        )
