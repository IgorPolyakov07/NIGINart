import logging
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from src.db.database import get_db
from src.models.metric import Metric
from src.models.account import Account
from src.models.schemas import YouTubeVideoResponse, YouTubeHistoryResponse
logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/youtube", tags=["YouTube"])
@router.get("/videos", response_model=list[YouTubeVideoResponse])
async def get_youtube_videos(
    account_id: Optional[str] = Query(None, description="Filter by account ID"),
    limit: int = Query(20, ge=1, le=100, description="Number of videos per page"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    sort_by: str = Query("date", regex="^(views|likes|comments|engagement|date)$", description="Sort field"),
    order: str = Query("desc", regex="^(asc|desc)$", description="Sort order"),
    db: AsyncSession = Depends(get_db)
) -> list[YouTubeVideoResponse]:
    try:
        stmt = select(Metric).join(Account).where(Account.platform == 'youtube')
        if account_id:
            stmt = stmt.where(Metric.account_id == account_id)
        stmt = stmt.order_by(Metric.collected_at.desc()).limit(10 if account_id else 100)
        result = await db.execute(stmt)
        metrics = result.scalars().all()
        if not metrics:
            return []
        all_videos = []
        for metric in metrics:
            extra_data = metric.extra_data or {}
            recent_videos = extra_data.get('recent_videos', [])
            for video in recent_videos:
                views = video.get('views', 0)
                likes = video.get('likes', 0)
                comments = video.get('comments', 0)
                engagement_rate = ((likes + comments) / views * 100) if views > 0 else 0
                all_videos.append({
                    'video_id': video.get('video_id', ''),
                    'title': video.get('title', 'Unknown'),
                    'published_at': video.get('published_at', ''),
                    'views': views,
                    'likes': likes,
                    'comments': comments,
                    'engagement_rate': round(engagement_rate, 2),
                    'account_id': str(metric.account_id)
                })
        reverse = (order == 'desc')
        if sort_by == 'views':
            all_videos.sort(key=lambda v: v['views'], reverse=reverse)
        elif sort_by == 'likes':
            all_videos.sort(key=lambda v: v['likes'], reverse=reverse)
        elif sort_by == 'comments':
            all_videos.sort(key=lambda v: v['comments'], reverse=reverse)
        elif sort_by == 'engagement':
            all_videos.sort(key=lambda v: v['engagement_rate'], reverse=reverse)
        else:
            all_videos.sort(
                key=lambda v: v['published_at'],
                reverse=reverse
            )
        paginated = all_videos[offset:offset + limit]
        logger.info(f"Retrieved {len(paginated)} videos (total: {len(all_videos)})")
        return paginated
    except Exception as e:
        logger.error(f"Error retrieving YouTube videos: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve videos: {str(e)}"
        )
@router.get("/top-videos", response_model=list[YouTubeVideoResponse])
async def get_top_videos(
    metric: str = Query(..., regex="^(views|likes|comments|engagement)$", description="Metric to rank by"),
    period: str = Query("30d", regex="^(7d|30d|90d|all)$", description="Time period"),
    limit: int = Query(5, ge=1, le=20, description="Number of top videos"),
    account_id: Optional[str] = Query(None, description="Filter by account ID"),
    db: AsyncSession = Depends(get_db)
) -> list[YouTubeVideoResponse]:
    try:
        stmt = select(Metric).join(Account).where(Account.platform == 'youtube')
        if account_id:
            stmt = stmt.where(Metric.account_id == account_id)
        stmt = stmt.order_by(Metric.collected_at.desc()).limit(10 if account_id else 100)
        result = await db.execute(stmt)
        metrics = result.scalars().all()
        if not metrics:
            return []
        all_videos = []
        for m in metrics:
            extra_data = m.extra_data or {}
            videos = extra_data.get('recent_videos', [])
            for video in videos:
                views = video.get('views', 0)
                likes = video.get('likes', 0)
                comments = video.get('comments', 0)
                engagement_rate = ((likes + comments) / views * 100) if views > 0 else 0
                all_videos.append({
                    'video_id': video.get('video_id', ''),
                    'title': video.get('title', 'Unknown'),
                    'published_at': video.get('published_at', ''),
                    'views': views,
                    'likes': likes,
                    'comments': comments,
                    'engagement_rate': round(engagement_rate, 2),
                    'account_id': str(m.account_id)
                })
        if metric == 'views':
            all_videos.sort(key=lambda v: v['views'], reverse=True)
        elif metric == 'likes':
            all_videos.sort(key=lambda v: v['likes'], reverse=True)
        elif metric == 'comments':
            all_videos.sort(key=lambda v: v['comments'], reverse=True)
        elif metric == 'engagement':
            all_videos.sort(key=lambda v: v['engagement_rate'], reverse=True)
        top_videos = all_videos[:limit]
        logger.info(f"Retrieved top {len(top_videos)} videos by {metric}")
        return top_videos
    except Exception as e:
        logger.error(f"Error retrieving top videos: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve top videos: {str(e)}"
        )
@router.get("/history", response_model=YouTubeHistoryResponse)
async def get_youtube_history(
    account_id: str = Query(..., description="YouTube account ID"),
    start_date: Optional[datetime] = Query(None, description="Start date (ISO 8601)"),
    end_date: Optional[datetime] = Query(None, description="End date (ISO 8601)"),
    granularity: str = Query("day", regex="^(day|week|month)$", description="Data granularity"),
    db: AsyncSession = Depends(get_db)
) -> YouTubeHistoryResponse:
    try:
        stmt = select(Metric).join(Account).where(
            and_(
                Account.platform == 'youtube',
                Metric.account_id == account_id
            )
        )
        if start_date:
            stmt = stmt.where(Metric.collected_at >= start_date)
        if end_date:
            stmt = stmt.where(Metric.collected_at <= end_date)
        stmt = stmt.order_by(Metric.collected_at.asc())
        result = await db.execute(stmt)
        metrics = result.scalars().all()
        if not metrics:
            logger.warning(f"No metrics found for account {account_id}")
            return YouTubeHistoryResponse(
                account_id=account_id,
                granularity=granularity,
                data=[]
            )
        data_points = []
        for m in metrics:
            extra_data = m.extra_data or {}
            metrics_30d = extra_data.get('metrics_30d', {})
            data_points.append({
                'timestamp': m.collected_at.isoformat(),
                'subscribers': m.followers or 0,
                'videos': m.posts_count or 0,
                'total_views': m.total_views or 0,
                'engagement_rate': m.engagement_rate or 0.0,
                'avg_likes': metrics_30d.get('avg_likes_per_video', 0.0)
            })
        logger.info(f"Retrieved {len(data_points)} data points for account {account_id}")
        return YouTubeHistoryResponse(
            account_id=account_id,
            granularity=granularity,
            data=data_points
        )
    except Exception as e:
        logger.error(f"Error retrieving YouTube history: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve history: {str(e)}"
        )
