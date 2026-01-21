import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from src.db.database import get_db
from src.models.metric import Metric
from src.models.account import Account
from src.models.schemas import (
    TelegramAccountResponse,
    TelegramMetricsResponse,
    TelegramTopPostsResponse,
    TelegramReactionsResponse,
    TelegramTemporalMetricsResponse,
)
logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/telegram", tags=["Telegram"])
@router.get("/accounts", response_model=List[TelegramAccountResponse])
async def get_telegram_accounts(
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: AsyncSession = Depends(get_db)
) -> List[TelegramAccountResponse]:
    try:
        query = select(Account).where(Account.platform == 'telegram')
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
                account_data['latest_metric'] = {
                    'followers': latest_metric.followers or 0,
                    'posts': latest_metric.posts_count or 0,
                    'total_views': latest_metric.total_views or 0,
                    'engagement_rate': latest_metric.engagement_rate or 0.0,
                    'collected_at': latest_metric.collected_at
                }
            response.append(account_data)
        logger.info(f"Retrieved {len(response)} Telegram accounts")
        return response
    except Exception as e:
        logger.error(f"Error retrieving Telegram accounts: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve Telegram accounts: {str(e)}"
        )
@router.get("/accounts/{account_id}/metrics", response_model=TelegramMetricsResponse)
async def get_telegram_metrics(
    account_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> TelegramMetricsResponse:
    try:
        query = (
            select(Metric)
            .join(Account)
            .where(
                and_(
                    Account.platform == 'telegram',
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
        response = {
            'account_id': account_id,
            'collected_at': metric.collected_at,
            'followers': metric.followers or 0,
            'posts': metric.posts_count or 0,
            'total_views': metric.total_views or 0,
            'total_likes': metric.total_likes or 0,
            'total_shares': metric.total_shares or 0,
            'engagement_rate': metric.engagement_rate or 0.0,
            'avg_views': extra_data.get('avg_views', 0),
            'avg_reactions': extra_data.get('avg_reactions', 0),
            'avg_forwards': extra_data.get('avg_forwards', 0),
            'err_views': extra_data.get('err_views', 0.0),
            'err_reactions': extra_data.get('err_reactions', 0.0),
            'reactions_breakdown': extra_data.get('reactions_breakdown', {}),
            'top_posts_by_views': extra_data.get('top_posts_by_views', []),
            'top_posts_by_reactions': extra_data.get('top_posts_by_reactions', []),
            'metrics_24h': extra_data.get('metrics_24h', {}),
            'metrics_7d': extra_data.get('metrics_7d', {}),
            'metrics_30d': extra_data.get('metrics_30d', {}),
            'sample_size': extra_data.get('sample_size', 0),
            'auth_mode': extra_data.get('auth_mode', 'unknown'),
            'has_extended_stats': extra_data.get('has_extended_stats', False),
        }
        logger.info(f"Retrieved metrics for Telegram account {account_id}")
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving Telegram metrics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve metrics: {str(e)}"
        )
@router.get("/accounts/{account_id}/top-posts", response_model=TelegramTopPostsResponse)
async def get_telegram_top_posts(
    account_id: UUID,
    sort_by: str = Query("views", regex="^(views|reactions|forwards)$", description="Sort by views, reactions, or forwards"),
    limit: int = Query(10, ge=1, le=50, description="Number of top posts to return"),
    db: AsyncSession = Depends(get_db)
) -> TelegramTopPostsResponse:
    try:
        query = (
            select(Metric)
            .join(Account)
            .where(
                and_(
                    Account.platform == 'telegram',
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
        all_posts = extra_data.get('top_posts_by_views', [])
        if sort_by == 'reactions':
            all_posts = sorted(all_posts, key=lambda x: x.get('reactions', 0), reverse=True)
        elif sort_by == 'forwards':
            all_posts = sorted(all_posts, key=lambda x: x.get('forwards', 0), reverse=True)
        top_posts = all_posts[:limit]
        response = {
            'account_id': account_id,
            'sort_by': sort_by,
            'limit': limit,
            'total_posts_available': len(all_posts),
            'top_posts': top_posts
        }
        logger.info(f"Retrieved top {limit} posts by {sort_by} for Telegram account {account_id}")
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving Telegram top posts: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve top posts: {str(e)}"
        )
@router.get("/accounts/{account_id}/reactions", response_model=TelegramReactionsResponse)
async def get_telegram_reactions(
    account_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> TelegramReactionsResponse:
    try:
        query = (
            select(Metric)
            .join(Account)
            .where(
                and_(
                    Account.platform == 'telegram',
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
        reactions_breakdown = extra_data.get('reactions_breakdown', {})
        total_reactions = sum(reactions_breakdown.values()) if reactions_breakdown else 0
        top_reaction = max(reactions_breakdown.items(), key=lambda x: x[1]) if reactions_breakdown else (None, 0)
        response = {
            'account_id': account_id,
            'total_reactions': total_reactions,
            'reaction_types_count': len(reactions_breakdown),
            'top_reaction': {
                'emoji': top_reaction[0],
                'count': top_reaction[1]
            } if top_reaction[0] else None,
            'reactions_breakdown': reactions_breakdown,
            'collected_at': metric.collected_at
        }
        logger.info(f"Retrieved reactions analytics for Telegram account {account_id}")
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving Telegram reactions: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve reactions: {str(e)}"
        )
@router.get("/accounts/{account_id}/temporal-metrics", response_model=TelegramTemporalMetricsResponse)
async def get_telegram_temporal_metrics(
    account_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> TelegramTemporalMetricsResponse:
    try:
        query = (
            select(Metric)
            .join(Account)
            .where(
                and_(
                    Account.platform == 'telegram',
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
        response = {
            'account_id': account_id,
            'metrics_24h': extra_data.get('metrics_24h', {}),
            'metrics_7d': extra_data.get('metrics_7d', {}),
            'metrics_30d': extra_data.get('metrics_30d', {}),
            'collected_at': metric.collected_at
        }
        logger.info(f"Retrieved temporal metrics for Telegram account {account_id}")
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving Telegram temporal metrics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve temporal metrics: {str(e)}"
        )
