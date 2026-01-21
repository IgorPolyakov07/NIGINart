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
    TikTokAccountResponse,
    TikTokMetricsResponse,
    TikTokHistoryResponse,
    TikTokContentAnalyticsResponse,
    TikTokVideoInfo,
    TikTokHistoryDataPoint,
)
from src.services.tiktok.content_analyzer import TikTokContentAnalyzer
logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/tiktok", tags=["TikTok"])
@router.get("/accounts", response_model=List[TikTokAccountResponse])
async def get_tiktok_accounts(
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: AsyncSession = Depends(get_db)
) -> List[TikTokAccountResponse]:
    try:
        query = select(Account).where(Account.platform == 'tiktok')
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
                    'videos': latest_metric.posts_count or 0,
                    'total_views': latest_metric.total_views or 0,
                    'engagement_rate': latest_metric.engagement_rate or 0.0,
                    'collected_at': latest_metric.collected_at
                }
            response.append(account_data)
        logger.info(f"Retrieved {len(response)} TikTok accounts")
        return response
    except Exception as e:
        logger.error(f"Error retrieving TikTok accounts: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve TikTok accounts: {str(e)}"
        )
@router.get("/accounts/{account_id}/metrics", response_model=TikTokMetricsResponse)
async def get_tiktok_metrics(
    account_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> TikTokMetricsResponse:
    try:
        query = (
            select(Metric)
            .join(Account)
            .where(
                and_(
                    Account.platform == 'tiktok',
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
        recent_videos = extra_data.get('recent_videos', [])
        ads_metrics = extra_data.get('ads_metrics')
        video_list = []
        for video in recent_videos:
            video_list.append({
                'video_id': video.get('video_id', ''),
                'title': video.get('title', ''),
                'published_at': video.get('published_at', ''),
                'views': video.get('views', 0),
                'likes': video.get('likes', 0),
                'comments': video.get('comments', 0),
                'shares': video.get('shares', 0),
                'engagement_rate': video.get('engagement_rate', 0.0),
                'duration': video.get('duration', 0)
            })
        response = {
            'account_id': account_id,
            'collected_at': metric.collected_at,
            'followers': metric.followers or 0,
            'videos': metric.posts_count or 0,
            'total_views': metric.total_views or 0,
            'total_likes': metric.total_likes or 0,
            'engagement_rate': metric.engagement_rate or 0.0,
            'recent_videos': video_list,
            'ads_metrics': ads_metrics
        }
        logger.info(f"Retrieved metrics for TikTok account {account_id}")
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving TikTok metrics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve metrics: {str(e)}"
        )
@router.get("/accounts/{account_id}/metrics/history", response_model=TikTokHistoryResponse)
async def get_tiktok_history(
    account_id: UUID,
    start_date: Optional[datetime] = Query(None, description="Start date (ISO 8601)"),
    end_date: Optional[datetime] = Query(None, description="End date (ISO 8601)"),
    limit: int = Query(100, ge=1, le=365, description="Maximum data points"),
    db: AsyncSession = Depends(get_db)
) -> TikTokHistoryResponse:
    try:
        query = (
            select(Metric)
            .join(Account)
            .where(
                and_(
                    Account.platform == 'tiktok',
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
            logger.warning(f"No metrics found for TikTok account {account_id}")
            return TikTokHistoryResponse(account_id=account_id, data=[])
        data_points = []
        for m in metrics:
            data_points.append({
                'timestamp': m.collected_at,
                'followers': m.followers or 0,
                'videos': m.posts_count or 0,
                'total_views': m.total_views or 0,
                'total_likes': m.total_likes or 0,
                'engagement_rate': m.engagement_rate or 0.0
            })
        logger.info(f"Retrieved {len(data_points)} historical data points for TikTok account {account_id}")
        return TikTokHistoryResponse(account_id=account_id, data=data_points)
    except Exception as e:
        logger.error(f"Error retrieving TikTok history: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve history: {str(e)}"
        )
@router.get("/accounts/{account_id}/analytics/content", response_model=TikTokContentAnalyticsResponse)
async def get_content_analytics(
    account_id: UUID,
    viral_threshold: float = Query(3.0, ge=1.5, le=5.0, description="Viral threshold multiplier"),
    db: AsyncSession = Depends(get_db)
) -> TikTokContentAnalyticsResponse:
    try:
        query = (
            select(Metric)
            .join(Account)
            .where(
                and_(
                    Account.platform == 'tiktok',
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
        recent_videos = extra_data.get('recent_videos', [])
        if not recent_videos:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No video data found for account {account_id}"
            )
        analyzer = TikTokContentAnalyzer(recent_videos)
        hashtag_analysis = analyzer.analyze_hashtags()
        posting_patterns = analyzer.analyze_posting_patterns()
        duration_analysis = analyzer.analyze_video_duration()
        viral_content = analyzer.detect_viral_content(threshold_multiplier=viral_threshold)
        response = {
            'account_id': account_id,
            'video_count': len(recent_videos),
            'analyzed_at': datetime.utcnow(),
            'hashtags': hashtag_analysis,
            'posting_patterns': posting_patterns,
            'duration_analysis': duration_analysis,
            'viral_content': viral_content
        }
        logger.info(f"Completed content analytics for TikTok account {account_id} ({len(recent_videos)} videos)")
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error performing content analytics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to perform content analytics: {str(e)}"
        )
