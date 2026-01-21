import asyncio
import logging
from datetime import date
from typing import Dict, List, Optional
import httpx
from src.services.tiktok.marketing_schemas import (
    Campaign,
    AdReportMetrics,
    AudienceReport
)
logger = logging.getLogger(__name__)
class TikTokMarketingClient:
    BASE_URL = "https://business-api.tiktok.com/open_api/v1.3"
    RATE_LIMIT = 10
    def __init__(self, access_token: str):
        self._semaphore = asyncio.Semaphore(self.RATE_LIMIT)
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={
                "Access-Token": access_token,
                "Content-Type": "application/json"
            },
            timeout=30.0
        )
        logger.debug("TikTok Marketing API client initialized")
    async def _request(self, method: str, endpoint: str, **kwargs) -> Dict:
        async with self._semaphore:
            response = await self._client.request(method, endpoint, **kwargs)
            response.raise_for_status()
            data = response.json()
            if data.get("code") != 0:
                error_msg = data.get("message", "Unknown error")
                logger.error(f"TikTok Marketing API error: {error_msg}")
                raise ValueError(f"TikTok Marketing API error: {error_msg}")
            return data.get("data", {})
    async def get_advertiser_info(self) -> Optional[Dict]:
        try:
            data = await self._request("GET", "/business/get/")
            businesses = data.get("list", [])
            if businesses:
                return businesses[0]
            return None
        except Exception as e:
            logger.warning(f"Failed to fetch advertiser info: {e}")
            return None
    async def get_campaigns(self, advertiser_id: str) -> List[Campaign]:
        try:
            data = await self._request(
                "GET",
                "/campaign/get/",
                params={
                    "advertiser_id": advertiser_id,
                    "fields": "campaign_id,campaign_name,objective_type,budget,status"
                }
            )
            campaigns = data.get("list", [])
            return [
                Campaign(
                    campaign_id=c.get("campaign_id", ""),
                    campaign_name=c.get("campaign_name", "Unnamed Campaign"),
                    objective_type=c.get("objective_type", "UNKNOWN"),
                    budget=c.get("budget"),
                    status=c.get("status", "UNKNOWN")
                )
                for c in campaigns
            ]
        except Exception as e:
            logger.error(f"Failed to fetch campaigns: {e}")
            return []
    async def get_ad_report(
        self,
        advertiser_id: str,
        start_date: date,
        end_date: date
    ) -> Dict:
        try:
            data = await self._request(
                "GET",
                "/report/integrated/get/",
                params={
                    "advertiser_id": advertiser_id,
                    "start_date": start_date.strftime("%Y-%m-%d"),
                    "end_date": end_date.strftime("%Y-%m-%d"),
                    "metrics": "impressions,clicks,spend,conversions,ctr,cpm,cpc,conversion_rate",
                    "data_level": "AUCTION_ADVERTISER"
                }
            )
            rows = data.get("list", [])
            if not rows:
                return {
                    "total_spend": 0.0,
                    "total_impressions": 0,
                    "total_clicks": 0,
                    "total_conversions": 0,
                    "avg_ctr": 0.0,
                    "avg_cpm": 0.0,
                    "avg_conversion_rate": 0.0
                }
            total_spend = sum(row.get("metrics", {}).get("spend", 0.0) for row in rows)
            total_impressions = sum(row.get("metrics", {}).get("impressions", 0) for row in rows)
            total_clicks = sum(row.get("metrics", {}).get("clicks", 0) for row in rows)
            total_conversions = sum(row.get("metrics", {}).get("conversions", 0) for row in rows)
            avg_ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0.0
            avg_cpm = (total_spend / total_impressions * 1000) if total_impressions > 0 else 0.0
            avg_conversion_rate = (total_conversions / total_clicks * 100) if total_clicks > 0 else 0.0
            return {
                "total_spend": round(total_spend, 2),
                "total_impressions": total_impressions,
                "total_clicks": total_clicks,
                "total_conversions": total_conversions,
                "avg_ctr": round(avg_ctr, 2),
                "avg_cpm": round(avg_cpm, 2),
                "avg_conversion_rate": round(avg_conversion_rate, 2)
            }
        except Exception as e:
            logger.error(f"Failed to fetch ad report: {e}")
            return {
                "total_spend": 0.0,
                "total_impressions": 0,
                "total_clicks": 0,
                "total_conversions": 0,
                "avg_ctr": 0.0,
                "avg_cpm": 0.0,
                "avg_conversion_rate": 0.0
            }
    async def get_audience_report(self, advertiser_id: str) -> AudienceReport:
        try:
            data = await self._request(
                "GET",
                "/audience/report/get/",
                params={
                    "advertiser_id": advertiser_id,
                    "dimensions": "age,gender,country,interest"
                }
            )
            age_data = data.get("age", [])
            age_distribution = {
                item.get("dimension_value"): item.get("percentage", 0.0)
                for item in age_data
            }
            gender_data = data.get("gender", [])
            gender_distribution = {
                item.get("dimension_value").lower(): item.get("percentage", 0.0)
                for item in gender_data
            }
            country_data = data.get("country", [])
            top_countries = [
                {
                    "country": item.get("dimension_value"),
                    "percentage": item.get("percentage", 0.0)
                }
                for item in country_data
            ]
            top_countries = sorted(top_countries, key=lambda x: x["percentage"], reverse=True)
            interest_data = data.get("interest", [])
            top_interests = [
                item.get("dimension_value")
                for item in sorted(interest_data, key=lambda x: x.get("percentage", 0.0), reverse=True)
            ]
            return AudienceReport(
                age_distribution=age_distribution,
                gender_distribution=gender_distribution,
                top_countries=top_countries,
                top_interests=top_interests
            )
        except Exception as e:
            logger.error(f"Failed to fetch audience report: {e}")
            return AudienceReport()
    async def close(self) -> None:
        await self._client.aclose()
        logger.debug("TikTok Marketing API client closed")
