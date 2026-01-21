import pytest
import httpx
import respx
from datetime import date, timedelta
from src.services.tiktok.marketing_client import TikTokMarketingClient
from src.services.tiktok.marketing_schemas import Campaign, AudienceReport
@pytest.mark.asyncio
async def test_get_campaigns_success():
    client = TikTokMarketingClient("test_access_token")
    with respx.mock:
        respx.get("https://business-api.tiktok.com/open_api/v1.3/campaign/get/").mock(
            return_value=httpx.Response(200, json={
                "code": 0,
                "data": {
                    "list": [
                        {
                            "campaign_id": "123456",
                            "campaign_name": "Summer Sale 2025",
                            "objective_type": "TRAFFIC",
                            "budget": 1000.0,
                            "status": "ENABLE"
                        },
                        {
                            "campaign_id": "789012",
                            "campaign_name": "Brand Awareness",
                            "objective_type": "REACH",
                            "budget": 500.0,
                            "status": "ENABLE"
                        }
                    ]
                }
            })
        )
        campaigns = await client.get_campaigns("advertiser_123")
        assert len(campaigns) == 2
        assert campaigns[0].campaign_name == "Summer Sale 2025"
        assert campaigns[0].objective_type == "TRAFFIC"
        assert campaigns[0].budget == 1000.0
        assert campaigns[1].campaign_name == "Brand Awareness"
    await client.close()
@pytest.mark.asyncio
async def test_get_campaigns_empty():
    client = TikTokMarketingClient("test_access_token")
    with respx.mock:
        respx.get("https://business-api.tiktok.com/open_api/v1.3/campaign/get/").mock(
            return_value=httpx.Response(200, json={
                "code": 0,
                "data": {
                    "list": []
                }
            })
        )
        campaigns = await client.get_campaigns("advertiser_123")
        assert len(campaigns) == 0
    await client.close()
@pytest.mark.asyncio
async def test_get_ad_report_success():
    client = TikTokMarketingClient("test_access_token")
    with respx.mock:
        respx.get("https://business-api.tiktok.com/open_api/v1.3/report/integrated/get/").mock(
            return_value=httpx.Response(200, json={
                "code": 0,
                "data": {
                    "list": [
                        {
                            "metrics": {
                                "impressions": 50000,
                                "clicks": 2500,
                                "spend": 250.0,
                                "conversions": 125
                            }
                        },
                        {
                            "metrics": {
                                "impressions": 50000,
                                "clicks": 2500,
                                "spend": 250.0,
                                "conversions": 125
                            }
                        }
                    ]
                }
            })
        )
        report = await client.get_ad_report(
            "advertiser_123",
            date.today() - timedelta(days=30),
            date.today()
        )
        assert report["total_spend"] == 500.0
        assert report["total_impressions"] == 100000
        assert report["total_clicks"] == 5000
        assert report["total_conversions"] == 250
        assert report["avg_ctr"] == 5.0
        assert report["avg_cpm"] == 5.0
        assert report["avg_conversion_rate"] == 5.0
    await client.close()
@pytest.mark.asyncio
async def test_get_ad_report_empty():
    client = TikTokMarketingClient("test_access_token")
    with respx.mock:
        respx.get("https://business-api.tiktok.com/open_api/v1.3/report/integrated/get/").mock(
            return_value=httpx.Response(200, json={
                "code": 0,
                "data": {
                    "list": []
                }
            })
        )
        report = await client.get_ad_report(
            "advertiser_123",
            date.today() - timedelta(days=7),
            date.today()
        )
        assert report["total_spend"] == 0.0
        assert report["total_impressions"] == 0
        assert report["total_clicks"] == 0
        assert report["total_conversions"] == 0
        assert report["avg_ctr"] == 0.0
        assert report["avg_cpm"] == 0.0
        assert report["avg_conversion_rate"] == 0.0
    await client.close()
@pytest.mark.asyncio
async def test_get_audience_report_success():
    client = TikTokMarketingClient("test_access_token")
    with respx.mock:
        respx.get("https://business-api.tiktok.com/open_api/v1.3/audience/report/get/").mock(
            return_value=httpx.Response(200, json={
                "code": 0,
                "data": {
                    "age": [
                        {"dimension_value": "18-24", "percentage": 0.25},
                        {"dimension_value": "25-34", "percentage": 0.40},
                        {"dimension_value": "35-44", "percentage": 0.20}
                    ],
                    "gender": [
                        {"dimension_value": "MALE", "percentage": 0.60},
                        {"dimension_value": "FEMALE", "percentage": 0.40}
                    ],
                    "country": [
                        {"dimension_value": "US", "percentage": 0.50},
                        {"dimension_value": "GB", "percentage": 0.20},
                        {"dimension_value": "CA", "percentage": 0.15}
                    ],
                    "interest": [
                        {"dimension_value": "Fashion", "percentage": 0.30},
                        {"dimension_value": "Technology", "percentage": 0.25}
                    ]
                }
            })
        )
        audience = await client.get_audience_report("advertiser_123")
        assert audience.age_distribution["18-24"] == 0.25
        assert audience.age_distribution["25-34"] == 0.40
        assert audience.gender_distribution["male"] == 0.60
        assert audience.gender_distribution["female"] == 0.40
        assert len(audience.top_countries) == 3
        assert audience.top_countries[0]["country"] == "US"
        assert len(audience.top_interests) == 2
        assert "Fashion" in audience.top_interests
    await client.close()
@pytest.mark.asyncio
async def test_get_advertiser_info_success():
    client = TikTokMarketingClient("test_access_token")
    with respx.mock:
        respx.get("https://business-api.tiktok.com/open_api/v1.3/business/get/").mock(
            return_value=httpx.Response(200, json={
                "code": 0,
                "data": {
                    "list": [
                        {
                            "advertiser_id": "1234567890",
                            "advertiser_name": "NIGIN Art Business"
                        }
                    ]
                }
            })
        )
        info = await client.get_advertiser_info()
        assert info is not None
        assert info["advertiser_id"] == "1234567890"
        assert info["advertiser_name"] == "NIGIN Art Business"
    await client.close()
@pytest.mark.asyncio
async def test_get_advertiser_info_no_business_account():
    client = TikTokMarketingClient("test_access_token")
    with respx.mock:
        respx.get("https://business-api.tiktok.com/open_api/v1.3/business/get/").mock(
            return_value=httpx.Response(200, json={
                "code": 0,
                "data": {
                    "list": []
                }
            })
        )
        info = await client.get_advertiser_info()
        assert info is None
    await client.close()
@pytest.mark.asyncio
async def test_rate_limiting():
    client = TikTokMarketingClient("test_access_token")
    assert client._semaphore._value == 10
    await client.close()
@pytest.mark.asyncio
async def test_api_error_handling():
    client = TikTokMarketingClient("test_access_token")
    with respx.mock:
        respx.get("https://business-api.tiktok.com/open_api/v1.3/campaign/get/").mock(
            return_value=httpx.Response(200, json={
                "code": 40001,
                "message": "Invalid advertiser_id"
            })
        )
        campaigns = await client.get_campaigns("invalid_advertiser")
        assert len(campaigns) == 0
    await client.close()
@pytest.mark.asyncio
async def test_http_error_handling():
    client = TikTokMarketingClient("test_access_token")
    with respx.mock:
        respx.get("https://business-api.tiktok.com/open_api/v1.3/campaign/get/").mock(
            return_value=httpx.Response(401, json={"error": "Unauthorized"})
        )
        campaigns = await client.get_campaigns("advertiser_123")
        assert len(campaigns) == 0
    await client.close()
