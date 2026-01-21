import pytest
from src.models.account import Account
@pytest.mark.asyncio
async def test_create_account(db_session):
    account = Account(
        platform="instagram",
        account_id="test_account",
        account_url="https://instagram.com/test_account",
        display_name="Test Account",
        is_active=True,
    )
    db_session.add(account)
    await db_session.commit()
    await db_session.refresh(account)
    assert account.id is not None
    assert account.platform == "instagram"
    assert account.account_id == "test_account"
    assert account.is_active is True
    assert account.created_at is not None
    assert account.updated_at is not None
@pytest.mark.asyncio
async def test_account_repr(db_session):
    account = Account(
        platform="telegram",
        account_id="channel_id",
        account_url="https://t.me/channel_id",
        display_name="Test Channel",
        is_active=True,
    )
    assert repr(account) == "<Account telegram:channel_id>"
