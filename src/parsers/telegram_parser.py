import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, List, Any
import logging
import json
from telethon import TelegramClient
from telethon.errors import FloodWaitError, RPCError
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.functions.messages import GetHistoryRequest
from telethon.tl.functions.stats import GetBroadcastStatsRequest
from telethon.tl.types import (
    Channel,
    Message,
    MessageReactions,
    ReactionEmoji,
    ReactionCustomEmoji,
    StatsGraph,
    StatsGraphAsync,
    StatsGraphError,
)
from telethon.tl.functions.stats import LoadAsyncGraphRequest
from src.parsers.base import BaseParser, PlatformMetrics
from src.parsers.utils import retry_async
from src.config.settings import get_settings
logger = logging.getLogger(__name__)
settings = get_settings()
class TelegramParser(BaseParser):
    POSTS_LIMIT = 100
    def __init__(self, account_id: str, account_url: str):
        super().__init__(account_id, account_url)
        self.client: Optional[TelegramClient] = None
    def get_platform_name(self) -> str:
        return "telegram"
    async def _init_client(self) -> None:
        if self.client is None:
            session_name = "telegram_bot_session" if settings.telegram_bot_token else settings.telegram_session_file
            self.client = TelegramClient(
                session_name,
                settings.telegram_api_id,
                settings.telegram_api_hash,
                timeout=settings.api_timeout_seconds
            )
            if settings.telegram_bot_token:
                logger.info("Using Telegram Bot token for authentication")
                await self.client.start(bot_token=settings.telegram_bot_token)
                logger.info("Telegram bot client connected successfully")
            else:
                await self.client.connect()
                if not await self.client.is_user_authorized():
                    logger.error("Telegram client not authorized")
                    raise RuntimeError(
                        "Telegram authentication required. Either set TELEGRAM_BOT_TOKEN or run: python scripts/init_telegram_session.py"
                    )
    async def is_available(self) -> bool:
        try:
            await self._init_client()
            return self.client.is_connected()
        except Exception as e:
            logger.error(f"Telegram availability check failed: {e}")
            return False
    async def _parse_graph(self, graph: Any) -> Optional[Dict[str, Any]]:
        if graph is None:
            return None
        if isinstance(graph, StatsGraphError):
            logger.warning(f"Graph error: {graph.error}")
            return None
        if isinstance(graph, StatsGraphAsync):
            try:
                graph = await self.client(LoadAsyncGraphRequest(token=graph.token))
            except Exception as e:
                logger.warning(f"Failed to load async graph: {e}")
                return None
        if isinstance(graph, StatsGraph):
            try:
                data = json.loads(graph.json.data)
                return {
                    "columns": data.get("columns", []),
                    "types": data.get("types", {}),
                    "names": data.get("names", {}),
                    "colors": data.get("colors", {}),
                }
            except Exception as e:
                logger.warning(f"Failed to parse graph JSON: {e}")
                return None
        return None
    async def _fetch_broadcast_stats(self, channel: Channel) -> Optional[Dict[str, Any]]:
        if settings.telegram_bot_token:
            logger.info("Extended stats not available with bot token, skipping")
            return None
        try:
            stats = await self.client(
                GetBroadcastStatsRequest(channel=channel, dark=False)
            )
            result = {
                "period_days": stats.period.max_date - stats.period.min_date if stats.period else None,
                "followers": {
                    "current": stats.followers.current if stats.followers else None,
                    "previous": stats.followers.previous if stats.followers else None,
                    "growth": (stats.followers.current - stats.followers.previous) if stats.followers else None,
                    "growth_percent": round(
                        ((stats.followers.current - stats.followers.previous) / stats.followers.previous * 100), 2
                    ) if stats.followers and stats.followers.previous else None,
                },
                "views_per_post": {
                    "current": stats.views_per_post.current if stats.views_per_post else None,
                    "previous": stats.views_per_post.previous if stats.views_per_post else None,
                },
                "shares_per_post": {
                    "current": stats.shares_per_post.current if stats.shares_per_post else None,
                    "previous": stats.shares_per_post.previous if stats.shares_per_post else None,
                },
                "reactions_per_post": {
                    "current": stats.reactions_per_post.current if stats.reactions_per_post else None,
                    "previous": stats.reactions_per_post.previous if stats.reactions_per_post else None,
                },
                "views_per_story": {
                    "current": stats.views_per_story.current if stats.views_per_story else None,
                    "previous": stats.views_per_story.previous if stats.views_per_story else None,
                } if hasattr(stats, 'views_per_story') and stats.views_per_story else None,
                "shares_per_story": {
                    "current": stats.shares_per_story.current if stats.shares_per_story else None,
                    "previous": stats.shares_per_story.previous if stats.shares_per_story else None,
                } if hasattr(stats, 'shares_per_story') and stats.shares_per_story else None,
                "reactions_per_story": {
                    "current": stats.reactions_per_story.current if stats.reactions_per_story else None,
                    "previous": stats.reactions_per_story.previous if stats.reactions_per_story else None,
                } if hasattr(stats, 'reactions_per_story') and stats.reactions_per_story else None,
                "enabled_notifications_percent": round(stats.enabled_notifications.part * 100, 2) if stats.enabled_notifications else None,
            }
            graphs_to_parse = {
                "followers_graph": stats.growth_graph,
                "views_graph": stats.views_graph,
                "mute_graph": stats.mute_graph,
                "top_hours_graph": stats.top_hours_graph,
                "interactions_graph": stats.interactions_graph,
                "iv_interactions_graph": stats.iv_interactions_graph,
                "reactions_by_emotion_graph": stats.reactions_by_emotion_graph,
                "story_interactions_graph": stats.story_interactions_graph if hasattr(stats, 'story_interactions_graph') else None,
                "story_reactions_graph": stats.story_reactions_graph if hasattr(stats, 'story_reactions_graph') else None,
            }
            for graph_name, graph in graphs_to_parse.items():
                if graph:
                    parsed = await self._parse_graph(graph)
                    if parsed:
                        result[graph_name] = parsed
            if stats.recent_posts_interactions:
                result["recent_posts_stats"] = []
                for post_stats in stats.recent_posts_interactions[:10]:
                    result["recent_posts_stats"].append({
                        "message_id": post_stats.msg_id,
                        "views": post_stats.views,
                        "forwards": post_stats.forwards,
                        "reactions": post_stats.reactions,
                    })
            logger.info("Successfully fetched extended broadcast statistics")
            return result
        except Exception as e:
            logger.warning(f"Could not fetch broadcast stats (may require 500+ subscribers): {e}")
            return None
    def _extract_reactions(self, message: Message) -> Dict[str, Any]:
        reactions_data = {
            "total": 0,
            "breakdown": {}
        }
        if not hasattr(message, 'reactions') or message.reactions is None:
            return reactions_data
        reactions: MessageReactions = message.reactions
        if not reactions.results:
            return reactions_data
        for reaction_count in reactions.results:
            count = reaction_count.count
            reactions_data["total"] += count
            reaction = reaction_count.reaction
            if isinstance(reaction, ReactionEmoji):
                emoji = reaction.emoticon
            elif isinstance(reaction, ReactionCustomEmoji):
                emoji = f"custom_{reaction.document_id}"
            else:
                emoji = "unknown"
            reactions_data["breakdown"][emoji] = reactions_data["breakdown"].get(emoji, 0) + count
        return reactions_data
    def _analyze_posts(self, posts: List[Message], subscribers: int) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        time_24h = now - timedelta(hours=24)
        time_7d = now - timedelta(days=7)
        time_30d = now - timedelta(days=30)
        total_views = 0
        total_forwards = 0
        total_reactions = 0
        reactions_breakdown: Dict[str, int] = {}
        posts_24h = []
        posts_7d = []
        posts_30d = []
        top_by_views: List[Dict] = []
        top_by_reactions: List[Dict] = []
        for msg in posts:
            if not isinstance(msg, Message):
                continue
            msg_date = msg.date
            if msg_date.tzinfo is None:
                msg_date = msg_date.replace(tzinfo=timezone.utc)
            views = getattr(msg, 'views', 0) or 0
            forwards = getattr(msg, 'forwards', 0) or 0
            total_views += views
            total_forwards += forwards
            msg_reactions = self._extract_reactions(msg)
            total_reactions += msg_reactions["total"]
            for emoji, count in msg_reactions["breakdown"].items():
                reactions_breakdown[emoji] = reactions_breakdown.get(emoji, 0) + count
            post_data = {
                "id": msg.id,
                "date": msg_date.isoformat(),
                "text": (msg.message or "")[:100] + "..." if msg.message and len(msg.message) > 100 else (msg.message or ""),
                "views": views,
                "forwards": forwards,
                "reactions": msg_reactions["total"],
                "reactions_breakdown": msg_reactions["breakdown"]
            }
            if msg_date >= time_24h:
                posts_24h.append(post_data)
            if msg_date >= time_7d:
                posts_7d.append(post_data)
            if msg_date >= time_30d:
                posts_30d.append(post_data)
            top_by_views.append(post_data)
            top_by_reactions.append(post_data)
        top_by_views = sorted(top_by_views, key=lambda x: x["views"], reverse=True)[:5]
        top_by_reactions = sorted(top_by_reactions, key=lambda x: x["reactions"], reverse=True)[:5]
        posts_count = len([m for m in posts if isinstance(m, Message)])
        avg_views = total_views / posts_count if posts_count > 0 else 0
        avg_forwards = total_forwards / posts_count if posts_count > 0 else 0
        avg_reactions = total_reactions / posts_count if posts_count > 0 else 0
        err_views = (avg_views / subscribers * 100) if subscribers > 0 else 0
        err_reactions = (avg_reactions / subscribers * 100) if subscribers > 0 else 0
        def calc_temporal_metrics(posts_list: List[Dict]) -> Dict:
            if not posts_list:
                return {"count": 0, "views": 0, "forwards": 0, "reactions": 0, "avg_views": 0}
            return {
                "count": len(posts_list),
                "views": sum(p["views"] for p in posts_list),
                "forwards": sum(p["forwards"] for p in posts_list),
                "reactions": sum(p["reactions"] for p in posts_list),
                "avg_views": sum(p["views"] for p in posts_list) / len(posts_list)
            }
        return {
            "total_views": total_views,
            "total_forwards": total_forwards,
            "total_reactions": total_reactions,
            "reactions_breakdown": reactions_breakdown,
            "posts_count": posts_count,
            "avg_views": round(avg_views, 2),
            "avg_forwards": round(avg_forwards, 2),
            "avg_reactions": round(avg_reactions, 2),
            "engagement_rate_views": round(err_views, 2),
            "engagement_rate_reactions": round(err_reactions, 2),
            "top_posts_by_views": top_by_views,
            "top_posts_by_reactions": top_by_reactions,
            "metrics_24h": calc_temporal_metrics(posts_24h),
            "metrics_7d": calc_temporal_metrics(posts_7d),
            "metrics_30d": calc_temporal_metrics(posts_30d),
        }
    async def fetch_metrics(self) -> PlatformMetrics:
        await self._init_client()
        async def _fetch() -> PlatformMetrics:
            entity = await self.client.get_entity(self.account_id)
            if not isinstance(entity, Channel):
                raise ValueError(f"Entity {self.account_id} is not a channel")
            try:
                full_channel = await self.client(GetFullChannelRequest(entity))
                full_chat = full_channel.full_chat
                subscribers = full_chat.participants_count or 0
                channel_info = {
                    "about": full_chat.about or "",
                    "admins_count": getattr(full_chat, 'admins_count', None),
                    "can_view_stats": getattr(full_chat, 'can_view_stats', False),
                    "linked_chat_id": getattr(full_chat, 'linked_chat_id', None),
                }
            except Exception as e:
                logger.warning(f"Could not get full channel info: {e}, using basic info")
                subscribers = entity.participants_count or 0
                channel_info = {}
            history = await self.client(GetHistoryRequest(
                peer=entity,
                limit=self.POSTS_LIMIT,
                offset_date=None,
                offset_id=0,
                max_id=0,
                min_id=0,
                add_offset=0,
                hash=0
            ))
            posts = history.messages
            analytics = self._analyze_posts(posts, subscribers)
            broadcast_stats = await self._fetch_broadcast_stats(entity)
            extra_data = {
                "channel_username": entity.username,
                "channel_title": entity.title,
                "channel_id": entity.id,
                **channel_info,
                "auth_mode": "bot" if settings.telegram_bot_token else "user",
                "sample_size": analytics["posts_count"],
                "avg_views": analytics["avg_views"],
                "avg_forwards": analytics["avg_forwards"],
                "avg_reactions": analytics["avg_reactions"],
                "err_views": analytics["engagement_rate_views"],
                "err_reactions": analytics["engagement_rate_reactions"],
                "reactions_breakdown": analytics["reactions_breakdown"],
                "top_posts_by_views": analytics["top_posts_by_views"],
                "top_posts_by_reactions": analytics["top_posts_by_reactions"],
                "metrics_24h": analytics["metrics_24h"],
                "metrics_7d": analytics["metrics_7d"],
                "metrics_30d": analytics["metrics_30d"],
            }
            if broadcast_stats:
                extra_data["broadcast_stats"] = broadcast_stats
                extra_data["has_extended_stats"] = True
            else:
                extra_data["has_extended_stats"] = False
            return PlatformMetrics(
                platform=self.get_platform_name(),
                account_id=self.account_id,
                collected_at=datetime.utcnow(),
                followers=subscribers,
                posts_count=analytics["posts_count"],
                total_views=analytics["total_views"],
                total_shares=analytics["total_forwards"],
                total_likes=analytics["total_reactions"],
                engagement_rate=analytics["engagement_rate_views"],
                extra_data=extra_data
            )
        return await retry_async(
            _fetch,
            max_attempts=settings.parser_retry_attempts,
            initial_delay=settings.parser_retry_delay
        )
    async def close(self) -> None:
        if self.client:
            await self.client.disconnect()
            logger.info("Telegram client disconnected")
