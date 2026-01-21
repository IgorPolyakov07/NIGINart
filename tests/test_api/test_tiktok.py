import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from typing import AsyncGenerator
from httpx import AsyncClient
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession
from src.main import app
from src.models.account import Account
from src.models.metric import Metric
from src.db.database import get_db
async def override_get_db(session: AsyncSession) -> AsyncGenerator[AsyncSession, None]:
    yield session
@pytest.fixture
async def test_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    app.dependency_overrides[get_db] = lambda: override_get_db(db_session)
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()
@pytest.mark.asyncio
async def test_get_tiktok_accounts_empty(test_client: AsyncClient):
    response = await test_client.get("/api/v1/tiktok/accounts")
    assert response.status_code == 200
    assert response.json() == []
@pytest.mark.asyncio
async def test_get_tiktok_accounts_with_data(test_client: AsyncClient, db_session: AsyncSession):
    account = Account(
        platform='tiktok',
        account_id='test_tiktok_account',
        account_url='https://tiktok.com/@test',
        display_name='Test TikTok Account',
        is_active=True
    )
    db_session.add(account)
    await db_session.commit()
    await db_session.refresh(account)
    metric = Metric(
        account_id=account.id,
        followers=10000,
        posts_count=50,
        total_views=500000,
        total_likes=25000,
        engagement_rate=5.5,
        collected_at=datetime.utcnow()
    )
    db_session.add(metric)
    await db_session.commit()
    response = await test_client.get("/api/v1/tiktok/accounts")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]['account_id'] == 'test_tiktok_account'
    assert data[0]['display_name'] == 'Test TikTok Account'
    assert data[0]['is_active'] is True
    assert data[0]['latest_metric'] is not None
    assert data[0]['latest_metric']['followers'] == 10000
    assert data[0]['latest_metric']['videos'] == 50
    assert data[0]['latest_metric']['engagement_rate'] == 5.5
@pytest.mark.asyncio
async def test_get_tiktok_accounts_filter_active(test_client: AsyncClient, db_session: AsyncSession):
    active_account = Account(
        platform='tiktok',
        account_id='active_tiktok',
        account_url='https://tiktok.com/@active',
        display_name='Active TikTok',
        is_active=True
    )
    db_session.add(active_account)
    inactive_account = Account(
        platform='tiktok',
        account_id='inactive_tiktok',
        account_url='https://tiktok.com/@inactive',
        display_name='Inactive TikTok',
        is_active=False
    )
    db_session.add(inactive_account)
    await db_session.commit()
    response = await test_client.get("/api/v1/tiktok/accounts?is_active=true")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]['account_id'] == 'active_tiktok'
    response = await test_client.get("/api/v1/tiktok/accounts?is_active=false")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]['account_id'] == 'inactive_tiktok'
@pytest.mark.asyncio
async def test_get_tiktok_accounts_no_metrics(test_client: AsyncClient, db_session: AsyncSession):
    account = Account(
        platform='tiktok',
        account_id='no_metrics',
        account_url='https://tiktok.com/@nometrics',
        display_name='No Metrics Account',
        is_active=True
    )
    db_session.add(account)
    await db_session.commit()
    response = await test_client.get("/api/v1/tiktok/accounts")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]['latest_metric'] is None
@pytest.mark.asyncio
async def test_get_tiktok_metrics_success(test_client: AsyncClient, db_session: AsyncSession):
    account = Account(
        platform='tiktok',
        account_id='test_metrics',
        account_url='https://tiktok.com/@test',
        display_name='Test Metrics',
        is_active=True
    )
    db_session.add(account)
    await db_session.commit()
    await db_session.refresh(account)
    recent_videos = [
        {
            'video_id': 'video1',
            'title': 'Test Video 1 #fashion #style',
            'published_at': '2025-01-01T12:00:00Z',
            'views': 10000,
            'likes': 500,
            'comments': 50,
            'shares': 25,
            'engagement_rate': 5.75,
            'duration': 30
        },
        {
            'video_id': 'video2',
            'title': 'Test Video 2',
            'published_at': '2025-01-02T12:00:00Z',
            'views': 20000,
            'likes': 1000,
            'comments': 100,
            'shares': 50,
            'engagement_rate': 5.75,
            'duration': 45
        }
    ]
    metric = Metric(
        account_id=account.id,
        followers=15000,
        posts_count=100,
        total_views=1000000,
        total_likes=50000,
        engagement_rate=6.0,
        collected_at=datetime.utcnow(),
        extra_data={'recent_videos': recent_videos}
    )
    db_session.add(metric)
    await db_session.commit()
    response = await test_client.get(f"/api/v1/tiktok/accounts/{account.id}/metrics")
    assert response.status_code == 200
    data = response.json()
    assert data['account_id'] == str(account.id)
    assert data['followers'] == 15000
    assert data['videos'] == 100
    assert data['engagement_rate'] == 6.0
    assert len(data['recent_videos']) == 2
    assert data['recent_videos'][0]['video_id'] == 'video1'
    assert data['recent_videos'][0]['title'] == 'Test Video 1 #fashion #style'
    assert data['ads_metrics'] is None
@pytest.mark.asyncio
async def test_get_tiktok_metrics_with_ads(test_client: AsyncClient, db_session: AsyncSession):
    account = Account(
        platform='tiktok',
        account_id='test_ads',
        account_url='https://tiktok.com/@test',
        display_name='Test Ads',
        is_active=True,
        advertiser_id='adv123'
    )
    db_session.add(account)
    await db_session.commit()
    await db_session.refresh(account)
    ads_metrics = {
        '30d': {
            'total_spend': 500.0,
            'total_impressions': 100000,
            'total_clicks': 5000,
            'total_conversions': 250,
            'avg_ctr': 5.0,
            'avg_cpm': 5.0,
            'avg_conversion_rate': 5.0
        }
    }
    metric = Metric(
        account_id=account.id,
        followers=20000,
        posts_count=75,
        total_views=750000,
        total_likes=40000,
        engagement_rate=5.3,
        collected_at=datetime.utcnow(),
        extra_data={
            'recent_videos': [],
            'ads_metrics': ads_metrics
        }
    )
    db_session.add(metric)
    await db_session.commit()
    response = await test_client.get(f"/api/v1/tiktok/accounts/{account.id}/metrics")
    assert response.status_code == 200
    data = response.json()
    assert data['ads_metrics'] is not None
    assert '30d' in data['ads_metrics']
    assert data['ads_metrics']['30d']['total_spend'] == 500.0
@pytest.mark.asyncio
async def test_get_tiktok_metrics_not_found(test_client: AsyncClient):
    fake_uuid = uuid4()
    response = await test_client.get(f"/api/v1/tiktok/accounts/{fake_uuid}/metrics")
    assert response.status_code == 404
    assert "No metrics found" in response.json()['detail']
@pytest.mark.asyncio
async def test_get_tiktok_history_success(test_client: AsyncClient, db_session: AsyncSession):
    account = Account(
        platform='tiktok',
        account_id='test_history',
        account_url='https://tiktok.com/@history',
        display_name='Test History',
        is_active=True
    )
    db_session.add(account)
    await db_session.commit()
    await db_session.refresh(account)
    base_date = datetime.utcnow() - timedelta(days=10)
    for i in range(5):
        metric = Metric(
            account_id=account.id,
            followers=10000 + (i * 1000),
            posts_count=50 + i,
            total_views=500000 + (i * 50000),
            total_likes=25000 + (i * 2500),
            engagement_rate=5.0 + (i * 0.1),
            collected_at=base_date + timedelta(days=i)
        )
        db_session.add(metric)
    await db_session.commit()
    response = await test_client.get(f"/api/v1/tiktok/accounts/{account.id}/metrics/history")
    assert response.status_code == 200
    data = response.json()
    assert data['account_id'] == str(account.id)
    assert len(data['data']) == 5
    assert data['data'][0]['followers'] == 10000
    assert data['data'][4]['followers'] == 14000
@pytest.mark.asyncio
async def test_get_tiktok_history_with_date_filter(test_client: AsyncClient, db_session: AsyncSession):
    account = Account(
        platform='tiktok',
        account_id='test_date_filter',
        account_url='https://tiktok.com/@filter',
        display_name='Test Filter',
        is_active=True
    )
    db_session.add(account)
    await db_session.commit()
    await db_session.refresh(account)
    start_date = datetime(2025, 1, 1, 0, 0, 0)
    for i in range(10):
        metric = Metric(
            account_id=account.id,
            followers=1000 * (i + 1),
            posts_count=10 + i,
            total_views=10000 * (i + 1),
            total_likes=500 * (i + 1),
            engagement_rate=5.0,
            collected_at=start_date + timedelta(days=i)
        )
        db_session.add(metric)
    await db_session.commit()
    filter_start = (start_date + timedelta(days=2)).isoformat()
    filter_end = (start_date + timedelta(days=5)).isoformat()
    response = await test_client.get(
        f"/api/v1/tiktok/accounts/{account.id}/metrics/history"
        f"?start_date={filter_start}&end_date={filter_end}"
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data['data']) == 4
@pytest.mark.asyncio
async def test_get_tiktok_history_empty(test_client: AsyncClient, db_session: AsyncSession):
    account = Account(
        platform='tiktok',
        account_id='no_history',
        account_url='https://tiktok.com/@nohistory',
        display_name='No History',
        is_active=True
    )
    db_session.add(account)
    await db_session.commit()
    await db_session.refresh(account)
    response = await test_client.get(f"/api/v1/tiktok/accounts/{account.id}/metrics/history")
    assert response.status_code == 200
    data = response.json()
    assert data['account_id'] == str(account.id)
    assert data['data'] == []
@pytest.mark.asyncio
async def test_get_content_analytics_success(test_client: AsyncClient, db_session: AsyncSession):
    account = Account(
        platform='tiktok',
        account_id='test_analytics',
        account_url='https://tiktok.com/@analytics',
        display_name='Test Analytics',
        is_active=True
    )
    db_session.add(account)
    await db_session.commit()
    await db_session.refresh(account)
    recent_videos = []
    base_date = datetime(2025, 1, 1, 12, 0, 0)
    for i in range(10):
        video = {
            'video_id': f'video{i}',
            'title': f'Test Video {i} #fashion #style',
            'published_at': (base_date + timedelta(days=i)).isoformat(),
            'views': 10000 * (i + 1),
            'likes': 500 * (i + 1),
            'comments': 50 * (i + 1),
            'shares': 25 * (i + 1),
            'engagement_rate': 5.0 + (i * 0.5),
            'duration': 30 + (i * 5)
        }
        recent_videos.append(video)
    metric = Metric(
        account_id=account.id,
        followers=50000,
        posts_count=200,
        total_views=5000000,
        total_likes=250000,
        engagement_rate=6.5,
        collected_at=datetime.utcnow(),
        extra_data={'recent_videos': recent_videos}
    )
    db_session.add(metric)
    await db_session.commit()
    response = await test_client.get(f"/api/v1/tiktok/accounts/{account.id}/analytics/content")
    assert response.status_code == 200
    data = response.json()
    assert data['account_id'] == str(account.id)
    assert data['video_count'] == 10
    assert 'analyzed_at' in data
    assert 'hashtags' in data
    assert 'posting_patterns' in data
    assert 'duration_analysis' in data
    assert 'viral_content' in data
    assert data['hashtags']['success'] is True
    assert len(data['hashtags']['hashtags']) >= 2
    assert data['posting_patterns']['success'] is True
    assert len(data['posting_patterns']['best_days']) > 0
    assert data['duration_analysis']['success'] is True
    assert len(data['duration_analysis']['duration_buckets']) > 0
    assert data['viral_content']['success'] is True
@pytest.mark.asyncio
async def test_get_content_analytics_custom_threshold(test_client: AsyncClient, db_session: AsyncSession):
    account = Account(
        platform='tiktok',
        account_id='test_threshold',
        account_url='https://tiktok.com/@threshold',
        display_name='Test Threshold',
        is_active=True
    )
    db_session.add(account)
    await db_session.commit()
    await db_session.refresh(account)
    recent_videos = [
        {
            'video_id': f'video{i}',
            'title': f'Video {i}',
            'published_at': datetime.utcnow().isoformat(),
            'views': 10000 if i < 4 else 100000,
            'likes': 500,
            'comments': 50,
            'shares': 25,
            'engagement_rate': 5.0,
            'duration': 30
        }
        for i in range(5)
    ]
    metric = Metric(
        account_id=account.id,
        followers=10000,
        posts_count=50,
        total_views=500000,
        total_likes=25000,
        engagement_rate=5.0,
        collected_at=datetime.utcnow(),
        extra_data={'recent_videos': recent_videos}
    )
    db_session.add(metric)
    await db_session.commit()
    response = await test_client.get(
        f"/api/v1/tiktok/accounts/{account.id}/analytics/content?viral_threshold=2.0"
    )
    assert response.status_code == 200
    data = response.json()
    assert data['viral_content']['success'] is True
    assert len(data['viral_content']['viral_videos']) > 0
@pytest.mark.asyncio
async def test_get_content_analytics_insufficient_videos(test_client: AsyncClient, db_session: AsyncSession):
    account = Account(
        platform='tiktok',
        account_id='test_insufficient',
        account_url='https://tiktok.com/@insufficient',
        display_name='Test Insufficient',
        is_active=True
    )
    db_session.add(account)
    await db_session.commit()
    await db_session.refresh(account)
    recent_videos = [
        {
            'video_id': 'video1',
            'title': 'Video 1',
            'published_at': datetime.utcnow().isoformat(),
            'views': 10000,
            'likes': 500,
            'comments': 50,
            'shares': 25,
            'engagement_rate': 5.0,
            'duration': 30
        },
        {
            'video_id': 'video2',
            'title': 'Video 2',
            'published_at': datetime.utcnow().isoformat(),
            'views': 15000,
            'likes': 750,
            'comments': 75,
            'shares': 35,
            'engagement_rate': 5.5,
            'duration': 45
        }
    ]
    metric = Metric(
        account_id=account.id,
        followers=5000,
        posts_count=25,
        total_views=250000,
        total_likes=12500,
        engagement_rate=5.0,
        collected_at=datetime.utcnow(),
        extra_data={'recent_videos': recent_videos}
    )
    db_session.add(metric)
    await db_session.commit()
    response = await test_client.get(f"/api/v1/tiktok/accounts/{account.id}/analytics/content")
    assert response.status_code == 200
    data = response.json()
    assert data['hashtags']['success'] is False
    assert data['posting_patterns']['success'] is False
    assert data['viral_content']['success'] is False
@pytest.mark.asyncio
async def test_get_content_analytics_no_videos(test_client: AsyncClient, db_session: AsyncSession):
    account = Account(
        platform='tiktok',
        account_id='test_no_videos',
        account_url='https://tiktok.com/@novideos',
        display_name='Test No Videos',
        is_active=True
    )
    db_session.add(account)
    await db_session.commit()
    await db_session.refresh(account)
    metric = Metric(
        account_id=account.id,
        followers=1000,
        posts_count=10,
        total_views=50000,
        total_likes=2500,
        engagement_rate=5.0,
        collected_at=datetime.utcnow(),
        extra_data={}
    )
    db_session.add(metric)
    await db_session.commit()
    response = await test_client.get(f"/api/v1/tiktok/accounts/{account.id}/analytics/content")
    assert response.status_code == 404
    assert "No video data found" in response.json()['detail']
@pytest.mark.asyncio
async def test_get_content_analytics_no_metrics(test_client: AsyncClient):
    fake_uuid = uuid4()
    response = await test_client.get(f"/api/v1/tiktok/accounts/{fake_uuid}/analytics/content")
    assert response.status_code == 404
    assert "No metrics found" in response.json()['detail']
