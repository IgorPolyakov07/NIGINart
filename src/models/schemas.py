from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
class AccountBase(BaseModel):
    platform: str = Field(..., max_length=50)
    account_id: str = Field(..., max_length=255)
    account_url: str = Field(..., max_length=500)
    display_name: str = Field(..., max_length=255)
    is_active: bool = True
class AccountCreate(AccountBase):
    pass
class AccountUpdate(BaseModel):
    display_name: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None
class AccountResponse(AccountBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
class MetricBase(BaseModel):
    followers: Optional[int] = None
    posts_count: Optional[int] = None
    total_likes: Optional[int] = None
    total_comments: Optional[int] = None
    total_views: Optional[int] = None
    total_shares: Optional[int] = None
    engagement_rate: Optional[float] = None
    extra_data: Optional[dict] = None
class MetricCreate(MetricBase):
    account_id: UUID
    collected_at: datetime
class MetricResponse(MetricBase):
    id: UUID
    account_id: UUID
    collected_at: datetime
    model_config = ConfigDict(from_attributes=True)
class CollectionLogResponse(BaseModel):
    id: UUID
    started_at: datetime
    finished_at: Optional[datetime] = None
    status: str
    accounts_processed: int
    accounts_failed: int
    error_message: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)
class HealthResponse(BaseModel):
    status: str
    version: str
    database: str
    timestamp: datetime
class CollectionTriggerRequest(BaseModel):
    platform: Optional[str] = Field(
        None,
        description="Optional platform filter (telegram, youtube, vk)",
        max_length=50
    )
class CollectionTriggerResponse(BaseModel):
    log_id: UUID = Field(..., description="Collection log UUID")
    status: str = Field(..., description="Collection status (success, partial, failed)")
    started_at: datetime = Field(..., description="When collection started")
    finished_at: Optional[datetime] = Field(None, description="When collection finished")
    accounts_processed: int = Field(..., description="Number of successfully processed accounts")
    accounts_failed: int = Field(..., description="Number of failed accounts")
    success_details: list = Field(default=[], description="Details of successful collections")
    error_details: list = Field(default=[], description="Details of failed collections")
class YouTubeVideoResponse(BaseModel):
    video_id: str = Field(..., description="YouTube video ID")
    title: str = Field(..., description="Video title")
    published_at: str = Field(..., description="Publication date (ISO 8601)")
    views: int = Field(..., description="View count")
    likes: int = Field(..., description="Like count")
    comments: int = Field(..., description="Comment count")
    engagement_rate: Optional[float] = Field(None, description="(likes + comments) / views * 100")
    account_id: Optional[str] = Field(None, description="Associated account ID")
    model_config = ConfigDict(from_attributes=True)
class YouTubeHistoryDataPoint(BaseModel):
    timestamp: str = Field(..., description="Timestamp (ISO 8601)")
    subscribers: int = Field(..., description="Subscriber count")
    videos: int = Field(..., description="Video count")
    total_views: int = Field(..., description="Total channel views")
    engagement_rate: float = Field(..., description="Engagement rate %")
    avg_likes: float = Field(..., description="Average likes per video (30d)")
    model_config = ConfigDict(from_attributes=True)
class YouTubeHistoryResponse(BaseModel):
    account_id: str = Field(..., description="YouTube account ID")
    granularity: str = Field(..., description="Data granularity (day/week/month)")
    data: list[YouTubeHistoryDataPoint] = Field(..., description="Historical data points")
    model_config = ConfigDict(from_attributes=True)
class TikTokOAuthStartResponse(BaseModel):
    authorization_url: str = Field(..., description="TikTok authorization URL to redirect user to")
    state: str = Field(..., description="CSRF state token")
class TikTokTokenResponse(BaseModel):
    access_token: str = Field(..., description="OAuth access token")
    refresh_token: str = Field(..., description="OAuth refresh token")
    expires_in: int = Field(..., description="Token lifetime in seconds")
    scope: str = Field(..., description="Granted scopes (comma-separated)")
    open_id: str = Field(..., description="TikTok user ID")
    token_type: str = Field(default="Bearer", description="Token type")
class TikTokUserInfo(BaseModel):
    open_id: str = Field(..., description="TikTok user ID")
    union_id: Optional[str] = Field(None, description="TikTok union ID (if available)")
    avatar_url: Optional[str] = Field(None, description="User avatar URL")
    avatar_url_100: Optional[str] = Field(None, description="User avatar URL (100x100)")
    avatar_large_url: Optional[str] = Field(None, description="User avatar URL (large)")
    display_name: str = Field(..., description="User display name")
    bio_description: Optional[str] = Field(None, description="User bio")
    profile_deep_link: Optional[str] = Field(None, description="TikTok profile deep link")
    is_verified: bool = Field(default=False, description="Is verified account")
    follower_count: int = Field(default=0, description="Number of followers")
    following_count: int = Field(default=0, description="Number of following")
    likes_count: int = Field(default=0, description="Total likes received")
    video_count: int = Field(default=0, description="Number of videos posted")
class TikTokVideoInfo(BaseModel):
    id: str = Field(..., description="Video ID")
    title: str = Field(..., description="Video title/caption")
    create_time: int = Field(..., description="Unix timestamp")
    cover_image_url: str = Field(..., description="Video cover image URL")
    share_url: str = Field(..., description="Share URL")
    video_description: Optional[str] = Field(None, description="Video description")
    duration: int = Field(..., description="Video duration in seconds")
    height: int = Field(..., description="Video height in pixels")
    width: int = Field(..., description="Video width in pixels")
    embed_html: Optional[str] = Field(None, description="Embed HTML code")
    embed_link: Optional[str] = Field(None, description="Embed link")
    like_count: int = Field(default=0, description="Number of likes")
    comment_count: int = Field(default=0, description="Number of comments")
    share_count: int = Field(default=0, description="Number of shares")
    view_count: int = Field(default=0, description="Number of views")
class InstagramOAuthStartResponse(BaseModel):
    authorization_url: str = Field(
        ..., description="Facebook authorization URL to redirect user to"
    )
    state: str = Field(..., description="CSRF state token")
class PinterestOAuthStartResponse(BaseModel):
    authorization_url: str = Field(
        ..., description="Pinterest authorization URL to redirect user to"
    )
    state: str = Field(..., description="CSRF state token")
class InstagramUserInfo(BaseModel):
    instagram_account_id: str = Field(..., description="Instagram Business Account ID")
    username: str = Field(..., description="Instagram @username")
    name: Optional[str] = Field(None, description="Display name")
    profile_picture_url: Optional[str] = Field(None, description="Profile picture URL")
    followers_count: int = Field(default=0, description="Number of followers")
    follows_count: int = Field(default=0, description="Number of accounts following")
    media_count: int = Field(default=0, description="Total number of posts")
class FacebookPageResponse(BaseModel):
    id: str = Field(..., description="Facebook Page ID")
    name: str = Field(..., description="Page name")
    category: Optional[str] = Field(None, description="Page category")
    has_instagram: bool = Field(..., description="Whether Page has Instagram Business Account")
    instagram_account_id: Optional[str] = Field(
        None, description="Instagram Business Account ID if linked"
    )
class TikTokLatestMetric(BaseModel):
    followers: int
    videos: int
    total_views: int
    engagement_rate: float
    collected_at: datetime
class TikTokAccountResponse(BaseModel):
    id: UUID
    account_id: str
    display_name: str
    is_active: bool
    created_at: datetime
    latest_metric: Optional[TikTokLatestMetric] = None
    model_config = ConfigDict(from_attributes=True)
class TikTokVideoInfo(BaseModel):
    video_id: str
    title: str
    published_at: str
    views: int
    likes: int
    comments: int
    shares: int
    engagement_rate: float
    duration: int
class TikTokAdsMetricsPeriod(BaseModel):
    total_spend: float
    total_impressions: int
    total_clicks: int
    total_conversions: int
    avg_ctr: float
    avg_cpm: float
    avg_conversion_rate: float
class TikTokMetricsResponse(BaseModel):
    account_id: UUID
    collected_at: datetime
    followers: int
    videos: int
    total_views: int
    total_likes: int
    engagement_rate: float
    recent_videos: List[TikTokVideoInfo]
    ads_metrics: Optional[dict] = None
class TikTokHistoryDataPoint(BaseModel):
    timestamp: datetime
    followers: int
    videos: int
    total_views: int
    total_likes: int
    engagement_rate: float
class TikTokHistoryResponse(BaseModel):
    account_id: UUID
    data: List[TikTokHistoryDataPoint]
class TikTokHashtagInfo(BaseModel):
    hashtag: str
    count: int
    avg_views: float
    avg_engagement: float
    trend: str
class TikTokBestDay(BaseModel):
    day: str
    avg_engagement: float
    video_count: int
class TikTokBestHour(BaseModel):
    hour: int
    avg_engagement: float
    video_count: int
class TikTokDurationBucket(BaseModel):
    bucket: str
    video_count: int
    avg_views: float
    avg_engagement: float
class TikTokViralVideo(BaseModel):
    video_id: str
    title: str
    views: int
    engagement_rate: float
    multiplier: float
    published_at: str
class TikTokHashtagAnalysis(BaseModel):
    success: bool
    message: str
    hashtags: List[TikTokHashtagInfo]
    total_unique_hashtags: int
    videos_with_hashtags: int
    videos_without_hashtags: int
class TikTokPostingPatterns(BaseModel):
    success: bool
    message: str
    best_days: List[TikTokBestDay]
    best_hours: List[TikTokBestHour]
    optimal_frequency: str
class TikTokDurationAnalysis(BaseModel):
    success: bool
    message: str
    duration_buckets: List[TikTokDurationBucket]
    optimal_duration: str
class TikTokViralContent(BaseModel):
    success: bool
    message: str
    threshold_views: float
    viral_videos: List[TikTokViralVideo]
    viral_rate: float
class TikTokContentAnalyticsResponse(BaseModel):
    account_id: UUID
    video_count: int
    analyzed_at: datetime
    hashtags: TikTokHashtagAnalysis
    posting_patterns: TikTokPostingPatterns
    duration_analysis: TikTokDurationAnalysis
    viral_content: TikTokViralContent
class InstagramStorySnapshotResponse(BaseModel):
    id: UUID
    story_id: str
    collected_at: datetime
    posted_at: datetime
    retention_expires_at: datetime
    media_type: str
    media_url: Optional[str] = None
    reach: Optional[int] = None
    impressions: Optional[int] = None
    exits: Optional[int] = None
    replies: Optional[int] = None
    taps_forward: Optional[int] = None
    taps_back: Optional[int] = None
    completion_rate: Optional[float] = None
    extra_data: Optional[dict] = None
    model_config = ConfigDict(from_attributes=True)
class InstagramStoriesCollectionResponse(BaseModel):
    status: str = Field(..., description="Collection status (success, partial, failed)")
    accounts_processed: int = Field(..., description="Number of successfully processed accounts")
    accounts_failed: int = Field(..., description="Number of failed accounts")
    total_snapshots_saved: int = Field(..., description="Total story snapshots saved")
    details: list = Field(..., description="Details of successful collections")
    errors: Optional[list] = Field(None, description="Details of failed collections")
class InstagramStoryHistoryResponse(BaseModel):
    account_id: UUID = Field(..., description="Instagram account UUID")
    account_name: str = Field(..., description="Account display name")
    since_hours: int = Field(..., description="Time window in hours")
    total_stories: int = Field(..., description="Total number of unique stories")
    total_snapshots: int = Field(..., description="Total number of snapshots")
    stories: list = Field(..., description="List of stories with their snapshots")
class InstagramTopPost(BaseModel):
    media_id: str = Field(..., description="Instagram media ID")
    caption: Optional[str] = Field(None, description="Post caption")
    media_type: str = Field(..., description="Media type (IMAGE, VIDEO, CAROUSEL_ALBUM)")
    saved: int = Field(..., description="Number of saves")
    reach: int = Field(..., description="Reach count")
    engagement_rate: float = Field(..., description="Engagement rate %")
    permalink: Optional[str] = Field(None, description="Instagram post URL")
class InstagramContentTypeStats(BaseModel):
    type: str = Field(..., description="Media type (IMAGE, VIDEO, CAROUSEL_ALBUM)")
    count: int = Field(..., description="Number of posts of this type")
    avg_saves: float = Field(..., description="Average saves per post")
    avg_reach: float = Field(..., description="Average reach per post")
    avg_likes: float = Field(..., description="Average likes per post")
    avg_engagement: float = Field(..., description="Average engagement per post")
    save_rate: float = Field(..., description="Save rate % (saves/reach * 100)")
class InstagramHashtagStats(BaseModel):
    hashtag: str = Field(..., description="Hashtag with # symbol")
    category: str = Field(..., description="Category (brand, product, style, trending)")
    posts_count: int = Field(..., description="Number of posts using this hashtag")
    avg_reach: int = Field(..., description="Average reach for posts with this hashtag")
    avg_saves: int = Field(..., description="Average saves for posts with this hashtag")
    save_rate: float = Field(..., description="Save rate % (saves/reach * 100)")
class InstagramBestDay(BaseModel):
    day: str = Field(..., description="Day of week abbreviation")
    avg_saves: int = Field(..., description="Average saves for this day")
    avg_engagement: int = Field(..., description="Average engagement for this day")
    post_count: int = Field(..., description="Number of posts on this day")
class InstagramBestHour(BaseModel):
    hour: str = Field(..., description="Hour in MSK timezone")
    avg_saves: int = Field(..., description="Average saves for this hour")
    avg_engagement: int = Field(..., description="Average engagement for this hour")
    post_count: int = Field(..., description="Number of posts at this hour")
class InstagramPostingPattern(BaseModel):
    success: bool = Field(..., description="Analysis success status")
    message: str = Field(..., description="Status message")
    best_days: list[InstagramBestDay] = Field(..., description="Top 3 best days for posting")
    best_hours: list[InstagramBestHour] = Field(..., description="Top 5 best hours for posting")
    timezone: str = Field(default="Moscow (UTC+3)", description="Timezone for hours")
    recommendation: str = Field(..., description="Posting time recommendation")
class InstagramCaptionAnalysis(BaseModel):
    success: bool = Field(..., description="Analysis success status")
    message: str = Field(..., description="Status message")
    avg_caption_length: int = Field(..., description="Average caption length")
    avg_emoji_count: float = Field(..., description="Average emoji count per caption")
    cta_posts_count: int = Field(..., description="Number of posts with CTA")
    non_cta_posts_count: int = Field(..., description="Number of posts without CTA")
    cta_avg_saves: int = Field(..., description="Average saves for CTA posts")
    non_cta_avg_saves: int = Field(..., description="Average saves for non-CTA posts")
    cta_effectiveness: str = Field(..., description="CTA effectiveness (higher/lower/similar/insufficient_data)")
class InstagramStoriesAnalysis(BaseModel):
    success: bool = Field(..., description="Analysis success status")
    message: str = Field(..., description="Status message")
    stories_analyzed: int = Field(..., description="Number of stories analyzed")
    total_reach: Optional[int] = Field(None, description="Total reach across all stories")
    total_impressions: Optional[int] = Field(None, description="Total impressions")
    total_replies: Optional[int] = Field(None, description="Total replies")
    avg_completion_rate: Optional[float] = Field(None, description="Average completion rate %")
    reply_rate: Optional[float] = Field(None, description="Reply rate % (replies/reach * 100)")
class InstagramFashionInsights(BaseModel):
    success: bool = Field(..., description="Analysis success status")
    message: str = Field(..., description="Status message")
    avg_save_rate: float = Field(..., description="Average save rate % (saves/reach * 100)")
    save_rate_benchmark: str = Field(..., description="Benchmark category (excellent/good/poor)")
    benchmark_description: str = Field(..., description="Benchmark description in Russian")
    best_performing_product: str = Field(..., description="Best performing product category")
    recommendation: str = Field(..., description="Actionable recommendation in Russian")
class InstagramContentAnalysisResponse(BaseModel):
    account_id: UUID = Field(..., description="Instagram account UUID")
    posts_analyzed: int = Field(..., description="Number of posts analyzed")
    top_posts_by_saves: list[InstagramTopPost] = Field(..., description="Top 5 posts by saves")
    content_types: Dict = Field(..., description="Content type performance analysis")
    hashtags: list[InstagramHashtagStats] = Field(..., description="Hashtag effectiveness analysis")
    posting_patterns: InstagramPostingPattern = Field(..., description="Optimal posting times")
    captions: InstagramCaptionAnalysis = Field(..., description="Caption pattern analysis")
    stories: InstagramStoriesAnalysis = Field(..., description="Stories performance analysis")
    insights_for_fashion_brand: InstagramFashionInsights = Field(..., description="Fashion-specific insights")
class InstagramCityStats(BaseModel):
    city: str = Field(..., description="City name")
    percentage: float = Field(..., description="Percentage of audience from this city")
class InstagramCountryStats(BaseModel):
    country: str = Field(..., description="Country code (e.g., RU, US)")
    percentage: float = Field(..., description="Percentage of audience from this country")
class InstagramDemographicsResponse(BaseModel):
    account_id: UUID = Field(..., description="Instagram account UUID")
    followers_count: int = Field(..., description="Total followers count")
    gender_distribution: Dict[str, float] = Field(
        ..., description="Gender distribution (M/F/U with percentages)"
    )
    age_distribution: Dict[str, float] = Field(
        ..., description="Age range distribution (e.g., '18-24': 0.25)"
    )
    top_cities: list[InstagramCityStats] = Field(
        ..., description="Top cities by audience percentage"
    )
    top_countries: list[InstagramCountryStats] = Field(
        ..., description="Top countries by audience percentage"
    )
class TelegramLatestMetric(BaseModel):
    followers: int
    posts: int
    total_views: int
    engagement_rate: float
    collected_at: datetime
class TelegramAccountResponse(BaseModel):
    id: UUID
    account_id: str
    display_name: str
    is_active: bool
    created_at: datetime
    latest_metric: Optional[TelegramLatestMetric] = None
    model_config = ConfigDict(from_attributes=True)
class TelegramTopPost(BaseModel):
    id: int
    date: str
    text: str
    views: int
    reactions: int
    forwards: int
class TelegramMetricsResponse(BaseModel):
    account_id: UUID
    collected_at: datetime
    followers: int
    posts: int
    total_views: int
    total_likes: int
    total_shares: int
    engagement_rate: float
    avg_views: float
    avg_reactions: float
    avg_forwards: float
    err_views: float
    err_reactions: float
    reactions_breakdown: Dict[str, int]
    top_posts_by_views: List[Dict[str, Any]]
    top_posts_by_reactions: List[Dict[str, Any]]
    metrics_24h: Dict[str, Any]
    metrics_7d: Dict[str, Any]
    metrics_30d: Dict[str, Any]
    sample_size: int
    auth_mode: str
    has_extended_stats: bool
class TelegramTopPostsResponse(BaseModel):
    account_id: UUID
    sort_by: str
    limit: int
    total_posts_available: int
    top_posts: List[TelegramTopPost]
class TelegramReactionsResponse(BaseModel):
    account_id: UUID
    total_reactions: int
    reaction_types_count: int
    top_reaction: Optional[Dict[str, Any]]
    reactions_breakdown: Dict[str, int]
    collected_at: datetime
class TelegramTemporalMetricsResponse(BaseModel):
    account_id: UUID
    metrics_24h: Dict[str, Any]
    metrics_7d: Dict[str, Any]
    metrics_30d: Dict[str, Any]
    collected_at: datetime
class PinterestLatestMetric(BaseModel):
    followers: int = Field(..., description="Number of followers")
    pins: int = Field(..., description="Total number of pins")
    monthly_views: int = Field(..., description="Monthly profile views")
    engagement_rate: float = Field(..., description="Engagement rate %")
    collected_at: datetime = Field(..., description="When metrics were collected")
class PinterestAccountResponse(BaseModel):
    id: UUID
    account_id: str = Field(..., description="Pinterest username")
    display_name: str = Field(..., description="Display name")
    is_active: bool = Field(..., description="Whether account is active")
    created_at: datetime = Field(..., description="When account was added")
    latest_metric: Optional[PinterestLatestMetric] = None
    model_config = ConfigDict(from_attributes=True)
class PinterestPinInfo(BaseModel):
    pin_id: str = Field(..., description="Pin ID")
    organic_pin_id: Optional[str] = Field(None, description="Organic pin ID")
    impressions: int = Field(default=0, description="Number of impressions")
    saves: int = Field(default=0, description="Number of saves")
    pin_clicks: int = Field(default=0, description="Number of pin clicks")
    outbound_clicks: int = Field(default=0, description="Number of outbound clicks")
class PinterestMetricsResponse(BaseModel):
    account_id: UUID = Field(..., description="Account UUID")
    collected_at: datetime = Field(..., description="Collection timestamp")
    followers: int = Field(..., description="Number of followers")
    pins: int = Field(..., description="Total number of pins")
    monthly_views: int = Field(..., description="Monthly profile views")
    engagement_rate: float = Field(..., description="Engagement rate %")
    impressions_30d: int = Field(default=0, description="Impressions in last 30 days")
    engagements_30d: int = Field(default=0, description="Engagements in last 30 days")
    saves_30d: int = Field(default=0, description="Saves in last 30 days")
    pin_clicks_30d: int = Field(default=0, description="Pin clicks in last 30 days")
    outbound_clicks_30d: int = Field(default=0, description="Outbound clicks in last 30 days")
    engagement_rate_30d: float = Field(default=0.0, description="30-day engagement rate %")
    save_rate_30d: float = Field(default=0.0, description="30-day save rate %")
    pin_click_rate_30d: float = Field(default=0.0, description="30-day pin click rate %")
    top_pins: List[PinterestPinInfo] = Field(default=[], description="Top performing pins")
    username: Optional[str] = Field(None, description="Pinterest username")
    business_name: Optional[str] = Field(None, description="Business name if set")
    board_count: int = Field(default=0, description="Number of boards")
    following_count: int = Field(default=0, description="Number of accounts following")
class PinterestHistoryDataPoint(BaseModel):
    timestamp: datetime = Field(..., description="Timestamp of the data point")
    followers: int = Field(..., description="Follower count")
    pins: int = Field(..., description="Pin count")
    monthly_views: int = Field(..., description="Monthly views")
    engagement_rate: float = Field(..., description="Engagement rate %")
class PinterestHistoryResponse(BaseModel):
    account_id: UUID = Field(..., description="Account UUID")
    data: List[PinterestHistoryDataPoint] = Field(..., description="Historical data points")
class PinterestTopPinsResponse(BaseModel):
    account_id: UUID = Field(..., description="Account UUID")
    sort_by: str = Field(..., description="Field used for sorting")
    limit: int = Field(..., description="Number of pins returned")
    pins: List[PinterestPinInfo] = Field(..., description="List of top pins")
