from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID
import logging
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.ext.asyncio import AsyncSession
from src.config.settings import get_settings
from src.models.account import Account
from src.db.repository import BaseRepository
logger = logging.getLogger(__name__)
settings = get_settings()
class TokenManager:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.account_repo = BaseRepository(Account, db)
        self._cipher = Fernet(settings.token_encryption_key.encode())
    def encrypt_token(self, token: str) -> str:
        return self._cipher.encrypt(token.encode()).decode()
    def decrypt_token(self, encrypted_token: str) -> Optional[str]:
        try:
            return self._cipher.decrypt(encrypted_token.encode()).decode()
        except InvalidToken:
            logger.error("Failed to decrypt token (invalid or corrupted)")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during token decryption: {e}")
            return None
    async def save_tokens(
        self,
        account_id: UUID,
        access_token: str,
        refresh_token: Optional[str],
        expires_in: int,
        scope: str,
    ) -> None:
        encrypted_access = self.encrypt_token(access_token)
        encrypted_refresh = self.encrypt_token(refresh_token) if refresh_token else None
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        await self.account_repo.update(
            account_id,
            encrypted_access_token=encrypted_access,
            encrypted_refresh_token=encrypted_refresh,
            token_expires_at=expires_at,
            token_scope=scope,
        )
        await self.db.commit()
        logger.info(
            f"Saved encrypted tokens for account {account_id}, "
            f"expires at {expires_at.isoformat()}"
        )
    async def get_valid_token(self, account: Account) -> Optional[str]:
        if not account.encrypted_access_token:
            logger.warning(f"Account {account.id} has no access token")
            return None
        access_token = self.decrypt_token(account.encrypted_access_token)
        if not access_token:
            logger.error(f"Failed to decrypt access token for account {account.id}")
            return None
        if account.token_expires_at:
            time_until_expiry = account.token_expires_at - datetime.utcnow()
            buffer = timedelta(days=7) if account.platform == "instagram" else timedelta(minutes=5)
            if time_until_expiry > buffer:
                logger.debug(
                    f"Using existing access token for {account.platform} account {account.id}, "
                    f"expires in {time_until_expiry.total_seconds():.0f}s"
                )
                return access_token
        logger.info(
            f"Access token for {account.platform} account {account.id} "
            f"expired/expiring soon, refreshing..."
        )
        if account.platform == "tiktok":
            return await self._refresh_tiktok_token(account)
        elif account.platform == "instagram":
            return await self._refresh_instagram_token(account, access_token)
        else:
            logger.error(f"Unknown platform {account.platform} for token refresh")
            return None
    async def _refresh_tiktok_token(self, account: Account) -> Optional[str]:
        if not account.encrypted_refresh_token:
            logger.error(f"TikTok account {account.id} has no refresh token")
            return None
        refresh_token = self.decrypt_token(account.encrypted_refresh_token)
        if not refresh_token:
            logger.error(f"Failed to decrypt refresh token for TikTok account {account.id}")
            return None
        from src.services.tiktok_oauth_service import TikTokOAuthService
        oauth_service = TikTokOAuthService()
        try:
            new_tokens = await oauth_service.refresh_access_token(refresh_token)
            await self.save_tokens(
                account.id,
                new_tokens["access_token"],
                new_tokens.get("refresh_token", refresh_token),
                new_tokens["expires_in"],
                new_tokens.get("scope", account.token_scope or ""),
            )
            logger.info(f"Successfully refreshed TikTok tokens for account {account.id}")
            return new_tokens["access_token"]
        except Exception as e:
            logger.error(
                f"Failed to refresh TikTok token for account {account.id}: {e}",
                exc_info=True,
            )
            return None
    async def _refresh_instagram_token(
        self, account: Account, current_access_token: str
    ) -> Optional[str]:
        from src.services.instagram.oauth_service import InstagramOAuthService
        oauth_service = InstagramOAuthService()
        token_age = datetime.utcnow() - account.updated_at
        if token_age.total_seconds() < 24 * 3600:
            logger.warning(
                f"Instagram token for account {account.id} too fresh to refresh "
                f"(age: {token_age.total_seconds() / 3600:.1f}h, need 24h+). "
                f"Returning current token."
            )
            return current_access_token
        try:
            new_tokens = await oauth_service.refresh_long_lived_token(current_access_token)
            await self.save_tokens(
                account.id,
                new_tokens["access_token"],
                None,
                new_tokens["expires_in"],
                account.token_scope or "",
            )
            logger.info(f"Successfully refreshed Instagram tokens for account {account.id}")
            return new_tokens["access_token"]
        except Exception as e:
            logger.error(
                f"Failed to refresh Instagram token for account {account.id}: {e}",
                exc_info=True,
            )
            return None
    async def revoke_tokens(self, account_id: UUID) -> None:
        account = await self.account_repo.get(account_id)
        if not account:
            logger.warning(f"Account {account_id} not found for token revocation")
            return
        if account.encrypted_access_token:
            access_token = self.decrypt_token(account.encrypted_access_token)
            if access_token:
                from src.services.tiktok_oauth_service import TikTokOAuthService
                oauth_service = TikTokOAuthService()
                try:
                    await oauth_service.revoke_token(access_token)
                    logger.info(f"Revoked token on TikTok for account {account_id}")
                except Exception as e:
                    logger.error(
                        f"Failed to revoke token on TikTok for account {account_id}: {e}"
                    )
        await self.account_repo.update(
            account_id,
            encrypted_access_token=None,
            encrypted_refresh_token=None,
            token_expires_at=None,
            token_scope=None,
        )
        await self.db.commit()
        logger.info(f"Deleted encrypted tokens from database for account {account_id}")
