import logging
from typing import Dict, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.database import get_db
from src.db.repository import BaseRepository
from src.models.account import Account
from src.models.metric import Metric
from src.models.schemas import (
    InstagramContentAnalysisResponse,
    InstagramDemographicsResponse,
    InstagramCityStats,
    InstagramCountryStats,
)
from src.services.instagram.content_analyzer import InstagramContentAnalyzer
from src.services.instagram.stories_collector_service import (
    InstagramStoriesCollectorService,
)
from src.services.token_manager import TokenManager
from src.config.settings import get_settings
logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/api/v1/instagram", tags=["Instagram Analytics"])
@router.post(
    "/{account_id}/analyze-content",
    response_model=InstagramContentAnalysisResponse,
    status_code=status.HTTP_200_OK,
)
async def analyze_instagram_content(
    account_id: UUID = Path(..., description="Instagram account UUID"),
    days: int = Query(30, description="Analyze last N days of posts", ge=1, le=90),
    include_stories: bool = Query(
        False, description="Include Stories performance analysis"
    ),
    db: AsyncSession = Depends(get_db),
) -> InstagramContentAnalysisResponse:
    try:
        account_repo = BaseRepository(Account, db)
        account = await account_repo.get(account_id)
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
        logger.info(
            f"Starting content analysis for Instagram account {account_id} (@{account.display_name})"
        )
        metric_repo = BaseRepository(Metric, db)
        query = (
            select(Metric)
            .where(Metric.account_id == account_id)
            .order_by(Metric.collected_at.desc())
            .limit(1)
        )
        result = await db.execute(query)
        latest_metric = result.scalar_one_or_none()
        if not latest_metric:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No metrics available for account {account_id}. Run data collection first.",
            )
        extra_data = latest_metric.extra_data or {}
        recent_media = extra_data.get("recent_media", [])
        if not recent_media:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No recent media data available for account {account_id}. Re-run collection to fetch media.",
            )
        logger.info(
            f"Found {len(recent_media)} media items for analysis (collected at {latest_metric.collected_at})"
        )
        stories_data = None
        if include_stories:
            try:
                stories_service = InstagramStoriesCollectorService(db)
                stories_snapshots = await stories_service.get_recent_stories(
                    account_id, hours=days * 24
                )
                stories_data = [
                    {
                        "story_id": s.story_id,
                        "reach": s.reach,
                        "impressions": s.impressions,
                        "replies": s.replies,
                        "exits": s.exits,
                        "completion_rate": s.completion_rate,
                    }
                    for s in stories_snapshots
                ]
                logger.info(f"Included {len(stories_data)} Stories snapshots in analysis")
            except Exception as e:
                logger.warning(
                    f"Failed to fetch Stories data for analysis: {e}. Continuing without Stories."
                )
                stories_data = None
        analyzer = InstagramContentAnalyzer(media=recent_media, stories=stories_data)
        analysis = analyzer.get_full_analysis()
        logger.info(
            f"Content analysis completed for account {account_id}. Analyzed {analysis['posts_analyzed']} posts."
        )
        return InstagramContentAnalysisResponse(
            account_id=account_id,
            posts_analyzed=analysis["posts_analyzed"],
            top_posts_by_saves=analysis["top_posts_by_saves"],
            content_types=analysis["content_types"],
            hashtags=analysis["hashtags"],
            posting_patterns=analysis["posting_patterns"],
            captions=analysis["captions"],
            stories=analysis["stories"],
            insights_for_fashion_brand=analysis["insights_for_fashion_brand"],
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to analyze content for account {account_id}: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Content analysis failed: {str(e)}",
        )
@router.get(
    "/{account_id}/demographics",
    response_model=InstagramDemographicsResponse,
    status_code=status.HTTP_200_OK,
)
async def get_instagram_demographics(
    account_id: UUID = Path(..., description="Instagram account UUID"),
    db: AsyncSession = Depends(get_db),
) -> InstagramDemographicsResponse:
    try:
        account_repo = BaseRepository(Account, db)
        account = await account_repo.get(account_id)
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
        logger.info(
            f"Fetching demographics for Instagram account {account_id} (@{account.display_name})"
        )
        metric_repo = BaseRepository(Metric, db)
        query = (
            select(Metric)
            .where(Metric.account_id == account_id)
            .order_by(Metric.collected_at.desc())
            .limit(1)
        )
        result = await db.execute(query)
        latest_metric = result.scalar_one_or_none()
        if not latest_metric:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No metrics available for account {account_id}. Run data collection first.",
            )
        followers_count = latest_metric.followers or 0
        if followers_count < 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Demographics data requires at least 100 followers. Current: {followers_count}",
            )
        access_token = await _get_access_token(db, account)
        import httpx
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"https://graph.facebook.com/{settings.facebook_graph_api_version}/{account.account_id}/insights",
                params={
                    "metric": "audience_gender_age,audience_city,audience_country",
                    "period": "lifetime",
                    "access_token": access_token,
                },
            )
            response.raise_for_status()
            insights_data = response.json()
        demographics = _parse_demographics(insights_data)
        logger.info(
            f"Demographics fetched successfully for account {account_id}"
        )
        return InstagramDemographicsResponse(
            account_id=account_id,
            followers_count=followers_count,
            gender_distribution=demographics["gender_distribution"],
            age_distribution=demographics["age_distribution"],
            top_cities=demographics["top_cities"],
            top_countries=demographics["top_countries"],
        )
    except HTTPException:
        raise
    except httpx.HTTPStatusError as e:
        logger.error(
            f"Instagram API error while fetching demographics: {e.response.status_code} - {e.response.text}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch demographics from Instagram API: {e.response.text}",
        )
    except Exception as e:
        logger.error(
            f"Failed to fetch demographics for account {account_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Demographics fetch failed: {str(e)}",
        )
async def _get_access_token(db: AsyncSession, account: Account) -> str:
    if settings.instagram_system_user_token:
        logger.info("Using System User Token for Instagram API")
        return settings.instagram_system_user_token
    token_manager = TokenManager(db)
    access_token = await token_manager.get_valid_token(account)
    if not access_token:
        raise RuntimeError(
            f"No valid token for Instagram account {account.display_name}. "
            "Please set INSTAGRAM_SYSTEM_USER_TOKEN or re-authorize via OAuth in dashboard."
        )
    logger.info(f"Using User OAuth token for Instagram account {account.display_name}")
    return access_token
def _parse_demographics(insights_data: Dict) -> Dict:
    result = {
        "gender_distribution": {},
        "age_distribution": {},
        "top_cities": [],
        "top_countries": [],
    }
    if "data" not in insights_data:
        logger.warning("No data in demographics insights response")
        return result
    for metric in insights_data["data"]:
        metric_name = metric.get("name")
        metric_values = metric.get("values", [])
        if not metric_values:
            continue
        metric_value = metric_values[0].get("value", {})
        if metric_name == "audience_gender_age":
            gender_totals = {"M": 0.0, "F": 0.0, "U": 0.0}
            age_totals = {}
            for key, percentage in metric_value.items():
                parts = key.split(".")
                if len(parts) == 2:
                    gender, age_range = parts
                    gender_totals[gender] = gender_totals.get(gender, 0.0) + percentage
                    age_totals[age_range] = age_totals.get(age_range, 0.0) + percentage
            result["gender_distribution"] = gender_totals
            result["age_distribution"] = age_totals
        elif metric_name == "audience_city":
            city_list = sorted(
                metric_value.items(), key=lambda x: x[1], reverse=True
            )[:10]
            result["top_cities"] = [
                InstagramCityStats(city=city, percentage=round(pct, 4))
                for city, pct in city_list
            ]
        elif metric_name == "audience_country":
            country_list = sorted(
                metric_value.items(), key=lambda x: x[1], reverse=True
            )[:10]
            result["top_countries"] = [
                InstagramCountryStats(country=country, percentage=round(pct, 4))
                for country, pct in country_list
            ]
    return result
