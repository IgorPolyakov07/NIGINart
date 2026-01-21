import logging
from typing import Dict, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import httpx
from src.db.database import get_db
from src.db.repository import BaseRepository
from src.models.account import Account
from src.models.metric import Metric
from src.services.token_manager import TokenManager
from src.config.settings import get_settings
logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/api/v1/instagram", tags=["Instagram Insights"])
@router.get("/{account_id}/demographics", status_code=status.HTTP_200_OK)
async def get_instagram_demographics(
    account_id: UUID = Path(..., description="Instagram account UUID"),
    db: AsyncSession = Depends(get_db),
) -> Dict:
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
        followers = latest_metric.followers or 0
        if followers < 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Demographics require 100+ followers. Current followers: {followers}",
            )
        logger.info(f"Account has {followers} followers, fetching demographics...")
        token_manager = TokenManager(db)
        access_token = await token_manager.get_valid_token(account)
        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"No valid access token for account {account_id}. Please reconnect the account.",
            )
        instagram_account_id = account.account_id
        graph_api_url = f"https://graph.facebook.com/{settings.facebook_graph_api_version}/{instagram_account_id}/insights"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                graph_api_url,
                params={
                    "metric": "audience_gender_age,audience_city,audience_country",
                    "period": "lifetime",
                    "access_token": access_token,
                },
            )
            response.raise_for_status()
            data = response.json().get("data", [])
            logger.info(
                f"Successfully fetched {len(data)} demographic metrics from Instagram API"
            )
            demographics: Dict = {
                "gender_distribution": {},
                "age_distribution": {},
                "top_cities": [],
            }
            for metric in data:
                metric_name = metric.get("name")
                values = metric.get("values", [{}])[0].get("value", {})
                if metric_name == "audience_gender_age":
                    male_total = sum(v for k, v in values.items() if k.startswith("M."))
                    female_total = sum(v for k, v in values.items() if k.startswith("F."))
                    total = male_total + female_total
                    if total > 0:
                        demographics["gender_distribution"] = {
                            "male": round(male_total / total, 4),
                            "female": round(female_total / total, 4),
                        }
                    age_groups = {}
                    for k, v in values.items():
                        if "." in k:
                            age = k.split(".")[1]
                            age_groups[age] = age_groups.get(age, 0) + v
                    total_age = sum(age_groups.values())
                    if total_age > 0:
                        demographics["age_distribution"] = {
                            age: round(count / total_age, 4)
                            for age, count in age_groups.items()
                        }
                elif metric_name == "audience_city":
                    sorted_cities = sorted(
                        values.items(), key=lambda x: x[1], reverse=True
                    )[:10]
                    demographics["top_cities"] = [
                        {"city": city, "percentage": round(pct, 4)}
                        for city, pct in sorted_cities
                    ]
            logger.info(
                f"Demographics parsed successfully: "
                f"{len(demographics['age_distribution'])} age groups, "
                f"{len(demographics['top_cities'])} cities"
            )
            return demographics
    except HTTPException:
        raise
    except httpx.HTTPStatusError as e:
        logger.error(
            f"Instagram API error for account {account_id}: {e.response.text}",
            exc_info=True,
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
            detail=f"Failed to fetch demographics: {str(e)}",
        )
