from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
@dataclass
class PlatformMetrics:
    platform: str
    account_id: str
    collected_at: datetime
    followers: Optional[int] = None
    posts_count: Optional[int] = None
    total_likes: Optional[int] = None
    total_comments: Optional[int] = None
    total_views: Optional[int] = None
    total_shares: Optional[int] = None
    engagement_rate: Optional[float] = None
    extra_data: Optional[dict] = None
class BaseParser(ABC):
    def __init__(self, account_id: str, account_url: str):
        self.account_id = account_id
        self.account_url = account_url
    @abstractmethod
    async def fetch_metrics(self) -> PlatformMetrics:
        pass
    @abstractmethod
    def get_platform_name(self) -> str:
        pass
    @abstractmethod
    async def is_available(self) -> bool:
        pass
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.account_id}>"
