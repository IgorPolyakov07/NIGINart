import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from src.db.database import get_db
from src.models.metric import Metric
from src.models.account import Account
from src.models.schemas import (
    PinterestAccountResponse,
    PinterestMetricsResponse,
    PinterestHistoryResponse,
    PinterestTopPinsResponse,
    PinterestPinInfo,
    PinterestHistoryDataPoint,
)
logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/pinterest", tags=["Pinterest"])
@router.get("/accounts", response_model=List[PinterestAccountResponse])
async def get_pinterest_accounts(
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: AsyncSession = Depends(get_db)
) -> List[PinterestAccountResponse]:
    try:
        query = select(Account).where(Account.platform == 'pinterest')
        if is_active is not None:
            query = query.where(Account.is_active == is_active)
        query = query.order_by(Account.display_name)
        result = await db.execute(query)
        accounts = result.scalars().all()
        response = []
        for account in accounts:
            metric_query = (
                select(Metric)
                .where(Metric.account_id == account.id)
                .order_by(Metric.collected_at.desc())
                .limit(1)
            )
            metric_result = await db.execute(metric_query)
            latest_metric = metric_result.scalar_one_or_none()
            account_data = {
                'id': account.id,
                'account_id': account.account_id,
                'display_name': account.display_name,
                'is_active': account.is_active,
                'created_at': account.created_at,
                'latest_metric': None
            }
            if latest_metric:
                extra_data = latest_metric.extra_data or {}
                account_data['latest_metric'] = {
                    'followers': latest_metric.followers or 0,
                    'pins': latest_metric.posts_count or 0,
                    'monthly_views': latest_metric.total_views or 0,
                    'engagement_rate': latest_metric.engagement_rate or 0.0,
                    'collected_at': latest_metric.collected_at
                }
            response.append(account_data)
        logger.info(f"Retrieved {len(response)} Pinterest accounts")
        return response
    except Exception as e:
        logger.error(f"Error retrieving Pinterest accounts: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve Pinterest accounts: {str(e)}"
        )
@router.get("/accounts/{account_id}/metrics", response_model=PinterestMetricsResponse)
async def get_pinterest_metrics(
    account_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> PinterestMetricsResponse:
    try:
        query = (
            select(Metric)
            .join(Account)
            .where(
                and_(
                    Account.platform == 'pinterest',
                    Metric.account_id == account_id
                )
            )
            .order_by(Metric.collected_at.desc())
            .limit(1)
        )
        result = await db.execute(query)
        metric = result.scalar_one_or_none()
        if not metric:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No metrics found for account {account_id}"
            )
        extra_data = metric.extra_data or {}
        top_pins_raw = extra_data.get('top_pins', [])
        top_pins = []
        for pin in top_pins_raw:
            top_pins.append(PinterestPinInfo(
                pin_id=pin.get('pin_id', ''),
                organic_pin_id=pin.get('organic_pin_id'),
                impressions=pin.get('impressions', 0),
                saves=pin.get('saves', 0),
                pin_clicks=pin.get('pin_clicks', 0),
                outbound_clicks=pin.get('outbound_clicks', 0)
            ))
        response = PinterestMetricsResponse(
            account_id=account_id,
            collected_at=metric.collected_at,
            followers=metric.followers or 0,
            pins=metric.posts_count or 0,
            monthly_views=metric.total_views or 0,
            engagement_rate=metric.engagement_rate or 0.0,
            impressions_30d=extra_data.get('impressions_30d', 0),
            engagements_30d=extra_data.get('engagements_30d', 0),
            saves_30d=extra_data.get('saves_30d', 0),
            pin_clicks_30d=extra_data.get('pin_clicks_30d', 0),
            outbound_clicks_30d=extra_data.get('outbound_clicks_30d', 0),
            engagement_rate_30d=extra_data.get('engagement_rate_30d', 0.0),
            save_rate_30d=extra_data.get('save_rate_30d', 0.0),
            pin_click_rate_30d=extra_data.get('pin_click_rate_30d', 0.0),
            top_pins=top_pins,
            username=extra_data.get('username'),
            business_name=extra_data.get('business_name'),
            board_count=extra_data.get('board_count', 0),
            following_count=extra_data.get('following_count', 0)
        )
        logger.info(f"Retrieved metrics for Pinterest account {account_id}")
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving Pinterest metrics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve metrics: {str(e)}"
        )
@router.get("/accounts/{account_id}/metrics/history", response_model=PinterestHistoryResponse)
async def get_pinterest_history(
    account_id: UUID,
    start_date: Optional[datetime] = Query(None, description="Start date (ISO 8601)"),
    end_date: Optional[datetime] = Query(None, description="End date (ISO 8601)"),
    limit: int = Query(100, ge=1, le=365, description="Maximum data points"),
    db: AsyncSession = Depends(get_db)
) -> PinterestHistoryResponse:
    try:
        query = (
            select(Metric)
            .join(Account)
            .where(
                and_(
                    Account.platform == 'pinterest',
                    Metric.account_id == account_id
                )
            )
        )
        if start_date:
            query = query.where(Metric.collected_at >= start_date)
        if end_date:
            query = query.where(Metric.collected_at <= end_date)
        query = query.order_by(Metric.collected_at.asc()).limit(limit)
        result = await db.execute(query)
        metrics = result.scalars().all()
        if not metrics:
            logger.warning(f"No metrics found for Pinterest account {account_id}")
            return PinterestHistoryResponse(account_id=account_id, data=[])
        data_points = []
        for m in metrics:
            data_points.append(PinterestHistoryDataPoint(
                timestamp=m.collected_at,
                followers=m.followers or 0,
                pins=m.posts_count or 0,
                monthly_views=m.total_views or 0,
                engagement_rate=m.engagement_rate or 0.0
            ))
        logger.info(f"Retrieved {len(data_points)} historical data points for Pinterest account {account_id}")
        return PinterestHistoryResponse(account_id=account_id, data=data_points)
    except Exception as e:
        logger.error(f"Error retrieving Pinterest history: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve history: {str(e)}"
        )
@router.get("/accounts/{account_id}/top-pins", response_model=PinterestTopPinsResponse)
async def get_pinterest_top_pins(
    account_id: UUID,
    sort_by: str = Query("impressions", description="Sort field: impressions, saves, pin_clicks, outbound_clicks"),
    limit: int = Query(10, ge=1, le=50, description="Number of pins to return"),
    db: AsyncSession = Depends(get_db)
) -> PinterestTopPinsResponse:
    valid_sort_fields = ['impressions', 'saves', 'pin_clicks', 'outbound_clicks']
    if sort_by not in valid_sort_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid sort_by field. Must be one of: {', '.join(valid_sort_fields)}"
        )
    try:
        query = (
            select(Metric)
            .join(Account)
            .where(
                and_(
                    Account.platform == 'pinterest',
                    Metric.account_id == account_id
                )
            )
            .order_by(Metric.collected_at.desc())
            .limit(1)
        )
        result = await db.execute(query)
        metric = result.scalar_one_or_none()
        if not metric:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No metrics found for account {account_id}"
            )
        extra_data = metric.extra_data or {}
        top_pins_raw = extra_data.get('top_pins', [])
        if not top_pins_raw:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No pins data found for account {account_id}"
            )
        pins = []
        for pin in top_pins_raw:
            pins.append(PinterestPinInfo(
                pin_id=pin.get('pin_id', ''),
                organic_pin_id=pin.get('organic_pin_id'),
                impressions=pin.get('impressions', 0),
                saves=pin.get('saves', 0),
                pin_clicks=pin.get('pin_clicks', 0),
                outbound_clicks=pin.get('outbound_clicks', 0)
            ))
        pins.sort(key=lambda p: getattr(p, sort_by, 0), reverse=True)
        pins = pins[:limit]
        logger.info(f"Retrieved {len(pins)} top pins for Pinterest account {account_id} sorted by {sort_by}")
        return PinterestTopPinsResponse(
            account_id=account_id,
            sort_by=sort_by,
            limit=limit,
            pins=pins
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving Pinterest top pins: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve top pins: {str(e)}"
        )
