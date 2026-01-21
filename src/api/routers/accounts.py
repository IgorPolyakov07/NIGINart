from datetime import datetime
from typing import List, Optional
from uuid import UUID
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.db.database import get_db
from src.db.repository import BaseRepository
from src.models.account import Account
from src.models.metric import Metric
from src.models.collection_log import CollectionLog
from src.models.schemas import (
    AccountResponse,
    AccountUpdate,
    MetricResponse,
    CollectionLogResponse
)
logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["accounts"])
@router.get("/accounts", response_model=List[AccountResponse], status_code=status.HTTP_200_OK)
async def get_accounts(
    platform: Optional[str] = Query(None, description="Filter by platform (telegram, youtube, vk)"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: AsyncSession = Depends(get_db)
) -> List[AccountResponse]:
    try:
        query = select(Account)
        if platform:
            query = query.where(Account.platform == platform.lower())
        if is_active is not None:
            query = query.where(Account.is_active == is_active)
        query = query.order_by(Account.platform, Account.display_name)
        result = await db.execute(query)
        accounts = list(result.scalars().all())
        logger.info(f"Retrieved {len(accounts)} accounts (platform={platform}, is_active={is_active})")
        return accounts
    except Exception as e:
        logger.error(f"Failed to retrieve accounts: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve accounts: {str(e)}"
        )
@router.patch("/accounts/{account_id}", response_model=AccountResponse, status_code=status.HTTP_200_OK)
async def update_account(
    account_id: UUID,
    account_update: AccountUpdate,
    db: AsyncSession = Depends(get_db)
) -> AccountResponse:
    try:
        repo = BaseRepository(Account, db)
        account = await repo.get(account_id)
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Account with id {account_id} not found"
            )
        update_data = account_update.model_dump(exclude_unset=True)
        updated_account = await repo.update(account_id, **update_data)
        await db.commit()
        logger.info(f"Updated account {account_id}: {update_data}")
        return updated_account
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update account {account_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update account: {str(e)}"
        )
@router.get("/metrics", response_model=List[MetricResponse], status_code=status.HTTP_200_OK)
async def get_metrics(
    account_id: Optional[UUID] = Query(None, description="Filter by account ID"),
    platform: Optional[str] = Query(None, description="Filter by platform"),
    start_date: Optional[datetime] = Query(None, description="Start date (ISO 8601)"),
    end_date: Optional[datetime] = Query(None, description="End date (ISO 8601)"),
    limit: int = Query(1000, ge=1, le=10000, description="Maximum number of metrics to return"),
    db: AsyncSession = Depends(get_db)
) -> List[MetricResponse]:
    try:
        query = select(Metric)
        if account_id:
            query = query.where(Metric.account_id == account_id)
        if platform:
            query = query.join(Account).where(Account.platform == platform.lower())
        if start_date:
            query = query.where(Metric.collected_at >= start_date)
        if end_date:
            query = query.where(Metric.collected_at <= end_date)
        query = query.order_by(Metric.collected_at.desc())
        query = query.limit(limit)
        result = await db.execute(query)
        metrics = list(result.scalars().all())
        logger.info(
            f"Retrieved {len(metrics)} metrics "
            f"(account_id={account_id}, platform={platform}, "
            f"start={start_date}, end={end_date}, limit={limit})"
        )
        return metrics
    except Exception as e:
        logger.error(f"Failed to retrieve metrics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve metrics: {str(e)}"
        )
@router.get("/logs", response_model=List[CollectionLogResponse], status_code=status.HTTP_200_OK)
async def get_collection_logs(
    limit: int = Query(10, ge=1, le=100, description="Number of logs to return"),
    db: AsyncSession = Depends(get_db)
) -> List[CollectionLogResponse]:
    try:
        query = (
            select(CollectionLog)
            .order_by(CollectionLog.started_at.desc())
            .limit(limit)
        )
        result = await db.execute(query)
        logs = list(result.scalars().all())
        logger.info(f"Retrieved {len(logs)} collection logs (limit={limit})")
        return logs
    except Exception as e:
        logger.error(f"Failed to retrieve collection logs: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve collection logs: {str(e)}"
        )
