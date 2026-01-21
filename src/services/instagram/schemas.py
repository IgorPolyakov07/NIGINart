from pydantic import BaseModel, Field
from typing import Optional
class FacebookTokenResponse(BaseModel):
    access_token: str = Field(..., description="OAuth access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: Optional[int] = Field(None, description="Token lifetime in seconds")
class FacebookPage(BaseModel):
    id: str = Field(..., description="Facebook Page ID")
    name: str = Field(..., description="Page name")
    access_token: str = Field(..., description="Page access token")
    category: Optional[str] = Field(None, description="Page category")
    instagram_business_account: Optional[dict] = Field(
        None,
        description="Instagram Business Account: {'id': 'instagram_user_id'}"
    )
class InstagramUser(BaseModel):
    id: str = Field(..., description="Instagram Business Account ID")
    username: str = Field(..., description="Instagram @username")
    name: Optional[str] = Field(None, description="Display name")
    profile_picture_url: Optional[str] = Field(None, description="Profile picture URL")
    followers_count: int = Field(default=0, description="Number of followers")
    follows_count: int = Field(default=0, description="Number of accounts following")
    media_count: int = Field(default=0, description="Total number of posts")
    biography: Optional[str] = Field(None, description="Bio text")
    website: Optional[str] = Field(None, description="Website URL from bio")
class InstagramMedia(BaseModel):
    id: str = Field(..., description="Media ID")
    media_type: str = Field(..., description="Type: IMAGE, VIDEO, CAROUSEL_ALBUM")
    media_url: Optional[str] = Field(None, description="URL to media file")
    permalink: str = Field(..., description="Public URL to post")
    caption: Optional[str] = Field(None, description="Post caption")
    timestamp: str = Field(..., description="Publication timestamp (ISO 8601)")
    like_count: int = Field(default=0, description="Number of likes")
    comments_count: int = Field(default=0, description="Number of comments")
    impressions: Optional[int] = Field(None, description="Number of views")
    reach: Optional[int] = Field(None, description="Unique accounts reached")
    engagement: Optional[int] = Field(None, description="Total interactions")
    saved: Optional[int] = Field(None, description="Number of saves")
