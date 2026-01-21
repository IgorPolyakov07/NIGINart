import pytest
from datetime import datetime
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
import respx
from src.parsers.tiktok_parser import TikTokParser
from src.parsers.base import PlatformMetrics
from src.models.account import Account
@pytest.fixture
def mock_db():
    return AsyncMock()
@pytest.fixture
def mock_account():
    account = MagicMock(spec=Account)
    account.id = uuid4()
    account.platform = "tiktok"
    account.account_id = "niginart_official"
    account.display_name = "NIGIN Art"
    account.encrypted_access_token = "encrypted_token_data"
    account.encrypted_refresh_token = "encrypted_refresh_data"
    account.token_expires_at = datetime.utcnow()
    account.token_scope = "user.info.basic,user.info.stats,video.list"
    return account
@pytest.fixture
def parser(mock_db, mock_account):
    parser = TikTokParser(
        account_id="niginart_official",
        account_url="https://www.tiktok.com/@niginart_official"
    )
    parser.set_db_context(mock_db, mock_account.id)
    return parser
@pytest.mark.asyncio
async def test_get_platform_name(parser):
    assert parser.get_platform_name() == "tiktok"
@pytest.mark.asyncio
async def test_is_available_success(parser, mock_db, mock_account):
    with patch('src.parsers.tiktok_parser.TokenManager') as MockTokenManager,         patch('src.parsers.tiktok_parser.BaseRepository') as MockRepo:
        mock_token_manager = MockTokenManager.return_value
        mock_token_manager.get_valid_token = AsyncMock(return_value="valid_access_token")
        mock_repo = MockRepo.return_value
        mock_repo.get = AsyncMock(return_value=mock_account)
        with respx.mock:
            respx.get("https://open.tiktokapis.com/v2/user/info/").mock(
                return_value=httpx.Response(200, json={
                    "data": {
                        "user": {
                            "open_id": "123456",
                            "display_name": "NIGIN Art"
                        }
                    }
                })
            )
            is_available = await parser.is_available()
            assert is_available is True
@pytest.mark.asyncio
async def test_is_available_no_token(parser, mock_db, mock_account):
    with patch('src.parsers.tiktok_parser.TokenManager') as MockTokenManager,         patch('src.parsers.tiktok_parser.BaseRepository') as MockRepo:
        mock_token_manager = MockTokenManager.return_value
        mock_token_manager.get_valid_token = AsyncMock(return_value=None)
        mock_repo = MockRepo.return_value
        mock_repo.get = AsyncMock(return_value=mock_account)
        is_available = await parser.is_available()
        assert is_available is False
@pytest.mark.asyncio
async def test_fetch_metrics_success(parser, mock_db, mock_account):
    with patch('src.parsers.tiktok_parser.TokenManager') as MockTokenManager,         patch('src.parsers.tiktok_parser.BaseRepository') as MockRepo:
        mock_token_manager = MockTokenManager.return_value
        mock_token_manager.get_valid_token = AsyncMock(return_value="valid_access_token")
        mock_repo = MockRepo.return_value
        mock_repo.get = AsyncMock(return_value=mock_account)
        with respx.mock:
            respx.get("https://open.tiktokapis.com/v2/user/info/").mock(
                return_value=httpx.Response(200, json={
                    "data": {
                        "user": {
                            "open_id": "123456",
                            "display_name": "NIGIN Art",
                            "follower_count": 50000,
                            "following_count": 100,
                            "likes_count": 1000000,
                            "video_count": 150,
                            "bio_description": "Official NIGIN Art channel",
                            "avatar_url": "https://example.com/avatar.jpg",
                            "is_verified": True
                        }
                    }
                })
            )
            respx.post("https://open.tiktokapis.com/v2/video/list/").mock(
                return_value=httpx.Response(200, json={
                    "data": {
                        "videos": [
                            {
                                "id": "7123456789",
                                "title": "Amazing Art #1",
                                "create_time": 1703500800,
                                "view_count": 20000,
                                "like_count": 1200,
                                "comment_count": 80,
                                "share_count": 150,
                                "duration": 60
                            },
                            {
                                "id": "7123456790",
                                "title": "Tutorial #2",
                                "create_time": 1703414400,
                                "view_count": 15000,
                                "like_count": 900,
                                "comment_count": 60,
                                "share_count": 100,
                                "duration": 45
                            }
                        ]
                    }
                })
            )
            metrics = await parser.fetch_metrics()
            assert isinstance(metrics, PlatformMetrics)
            assert metrics.platform == "tiktok"
            assert metrics.account_id == "niginart_official"
            assert metrics.followers == 50000
            assert metrics.posts_count == 150
            assert metrics.total_likes == 2100
            assert metrics.total_views == 35000
            assert metrics.total_comments == 140
            assert metrics.total_shares == 250
            assert metrics.extra_data is not None
            assert metrics.extra_data["display_name"] == "NIGIN Art"
            assert metrics.extra_data["sample_videos"] == 2
            assert len(metrics.extra_data["recent_videos"]) == 2
            assert "avg_views_per_video" in metrics.extra_data
            assert "avg_engagement_rate" in metrics.extra_data
@pytest.mark.asyncio
async def test_fetch_metrics_no_db_context():
    parser = TikTokParser("test_account", "https://www.tiktok.com/@test")
    with pytest.raises(RuntimeError, match="Database context not set"):
        await parser.fetch_metrics()
@pytest.mark.asyncio
async def test_close(parser, mock_db, mock_account):
    with patch('src.parsers.tiktok_parser.TokenManager') as MockTokenManager,         patch('src.parsers.tiktok_parser.BaseRepository') as MockRepo:
        mock_token_manager = MockTokenManager.return_value
        mock_token_manager.get_valid_token = AsyncMock(return_value="valid_token")
        mock_repo = MockRepo.return_value
        mock_repo.get = AsyncMock(return_value=mock_account)
        await parser._get_client()
        assert parser._client is not None
        await parser.close()
        assert parser._client is None
@pytest.mark.asyncio
async def test_fetch_ads_metrics_success(parser, mock_db, mock_account):
    mock_account.advertiser_id = "1234567890"
    with patch('src.parsers.tiktok_parser.TokenManager') as MockTokenManager,         patch('src.parsers.tiktok_parser.BaseRepository') as MockRepo,         patch('src.parsers.tiktok_parser.TikTokMarketingClient') as MockMarketingClient:
        mock_token_manager = MockTokenManager.return_value
        mock_token_manager.get_valid_token = AsyncMock(return_value="valid_token")
        mock_repo = MockRepo.return_value
        mock_repo.get = AsyncMock(return_value=mock_account)
        mock_marketing = MockMarketingClient.return_value
        mock_marketing.get_campaigns = AsyncMock(return_value=[
            MagicMock(
                campaign_id="123",
                campaign_name="Test Campaign",
                objective_type="TRAFFIC",
                budget=1000.0,
                status="ENABLE"
            )
        ])
        mock_marketing.get_ad_report = AsyncMock(return_value={
            "total_spend": 500.0,
            "total_impressions": 100000,
            "total_clicks": 5000,
            "total_conversions": 250,
            "avg_ctr": 5.0,
            "avg_cpm": 5.0,
            "avg_conversion_rate": 5.0
        })
        mock_marketing.get_audience_report = AsyncMock(return_value=MagicMock(
            age_distribution={"18-24": 0.3},
            gender_distribution={"male": 0.6, "female": 0.4},
            top_countries=[{"country": "US", "percentage": 0.5}],
            top_interests=["Fashion", "Technology"]
        ))
        ads_data = await parser.fetch_ads_metrics()
        assert ads_data is not None
        assert "ads_metrics" in ads_data
        assert "7d" in ads_data["ads_metrics"]
        assert "30d" in ads_data["ads_metrics"]
        assert "90d" in ads_data["ads_metrics"]
        assert "lifetime" in ads_data["ads_metrics"]
        assert "audience_insights" in ads_data
        assert ads_data["ads_metrics"]["30d"]["total_spend"] == 500.0
@pytest.mark.asyncio
async def test_fetch_ads_metrics_graceful_degradation(parser, mock_db, mock_account):
    mock_account.advertiser_id = None
    with patch('src.parsers.tiktok_parser.TokenManager') as MockTokenManager,         patch('src.parsers.tiktok_parser.BaseRepository') as MockRepo:
        mock_token_manager = MockTokenManager.return_value
        mock_token_manager.get_valid_token = AsyncMock(return_value="valid_token")
        mock_repo = MockRepo.return_value
        mock_repo.get = AsyncMock(return_value=mock_account)
        ads_data = await parser.fetch_ads_metrics()
        assert ads_data is None
@pytest.mark.asyncio
async def test_fetch_metrics_includes_ads_data(parser, mock_db, mock_account):
    mock_account.advertiser_id = "1234567890"
    with patch('src.parsers.tiktok_parser.TokenManager') as MockTokenManager,         patch('src.parsers.tiktok_parser.BaseRepository') as MockRepo:
        mock_token_manager = MockTokenManager.return_value
        mock_token_manager.get_valid_token = AsyncMock(return_value="valid_token")
        mock_repo = MockRepo.return_value
        mock_repo.get = AsyncMock(return_value=mock_account)
        with respx.mock:
            respx.get("https://open.tiktokapis.com/v2/user/info/").mock(
                return_value=httpx.Response(200, json={
                    "data": {
                        "user": {
                            "open_id": "123456",
                            "display_name": "NIGIN Art",
                            "follower_count": 50000,
                            "following_count": 100,
                            "likes_count": 1000000,
                            "video_count": 150
                        }
                    }
                })
            )
            respx.post("https://open.tiktokapis.com/v2/video/list/").mock(
                return_value=httpx.Response(200, json={
                    "data": {
                        "videos": [
                            {
                                "id": "7123456789",
                                "title": "Test Video",
                                "create_time": 1703500800,
                                "view_count": 20000,
                                "like_count": 1200,
                                "comment_count": 80,
                                "share_count": 150
                            }
                        ]
                    }
                })
            )
            with patch.object(parser, 'fetch_ads_metrics', return_value={
                "ads_metrics": {
                    "30d": {
                        "total_spend": 500.0,
                        "total_impressions": 100000
                    }
                }
            }):
                metrics = await parser.fetch_metrics()
                assert "ads_metrics" in metrics.extra_data
                assert metrics.extra_data["ads_metrics"]["30d"]["total_spend"] == 500.0
                assert metrics.extra_data["ads_metrics"]["30d"]["total_impressions"] == 100000
@pytest.mark.asyncio
async def test_fetch_metrics_without_ads_data(parser, mock_db, mock_account):
    mock_account.advertiser_id = None
    with patch('src.parsers.tiktok_parser.TokenManager') as MockTokenManager,         patch('src.parsers.tiktok_parser.BaseRepository') as MockRepo:
        mock_token_manager = MockTokenManager.return_value
        mock_token_manager.get_valid_token = AsyncMock(return_value="valid_token")
        mock_repo = MockRepo.return_value
        mock_repo.get = AsyncMock(return_value=mock_account)
        with respx.mock:
            respx.get("https://open.tiktokapis.com/v2/user/info/").mock(
                return_value=httpx.Response(200, json={
                    "data": {
                        "user": {
                            "open_id": "123456",
                            "display_name": "NIGIN Art",
                            "follower_count": 50000,
                            "following_count": 100,
                            "likes_count": 1000000,
                            "video_count": 150
                        }
                    }
                })
            )
            respx.post("https://open.tiktokapis.com/v2/video/list/").mock(
                return_value=httpx.Response(200, json={
                    "data": {
                        "videos": [
                            {
                                "id": "7123456789",
                                "title": "Test Video",
                                "create_time": 1703500800,
                                "view_count": 20000,
                                "like_count": 1200,
                                "comment_count": 80,
                                "share_count": 150
                            }
                        ]
                    }
                })
            )
            metrics = await parser.fetch_metrics()
            assert metrics is not None
            assert metrics.platform == "tiktok"
            assert "ads_metrics" not in metrics.extra_data
            assert "display_name" in metrics.extra_data
