import logging
import re
from collections import Counter, defaultdict
from datetime import datetime
from statistics import mean
from typing import Dict, List, Optional
import pytz
logger = logging.getLogger(__name__)
class InstagramContentAnalyzer:
    MIN_POSTS_HASHTAG = 2
    MIN_POSTS_POSTING = 3
    MIN_POSTS_VIRAL = 3
    MIN_POSTS_CAPTION = 3
    BRAND_HASHTAGS = {"niginart", "нигинарт"}
    PRODUCT_HASHTAGS = {
        "dress", "платье", "платья",
        "skirt", "юбка", "юбки",
        "blouse", "блуза", "блузка",
        "top", "топ",
        "pants", "брюки",
        "coat", "пальто",
        "jacket", "куртка", "жакет"
    }
    STYLE_HASHTAGS = {
        "ootd", "outfit", "образ",
        "fashion", "мода", "style", "стиль",
        "look", "лук",
        "fashionblogger", "fashionista"
    }
    CTA_KEYWORDS = [
        "ссылка в био", "переходи", "заказ", "купить", "в наличии",
        "пиши в директ", "заказать", "доступно",
        "link in bio", "dm", "order now", "available now", "shop now",
        "get it now", "buy now"
    ]
    MOSCOW_TZ = pytz.timezone('Europe/Moscow')
    def __init__(
        self,
        media: Optional[List[Dict]] = None,
        stories: Optional[List[Dict]] = None
    ):
        self.media = media or []
        self.stories = stories or []
        self._validate_media()
    def _validate_media(self) -> None:
        if not self.media:
            logger.warning("No media data provided for analysis")
        else:
            logger.info(f"Initialized analyzer with {len(self.media)} media items")
    def get_top_performing(
        self,
        metric: str = "saves",
        limit: int = 10
    ) -> List[Dict]:
        if not self.media:
            return []
        sorted_media = sorted(
            self.media,
            key=lambda m: self._safe_numeric(m.get(metric, 0)),
            reverse=True
        )
        return sorted_media[:limit]
    def analyze_content_types(self) -> Dict:
        if len(self.media) < self.MIN_POSTS_POSTING:
            return {
                'success': False,
                'message': f'Insufficient data. Need at least {self.MIN_POSTS_POSTING} posts.',
                'types': [],
                'recommendation': 'Collect more posts for analysis'
            }
        type_stats = defaultdict(lambda: {
            'posts': [],
            'count': 0,
            'total_saves': 0,
            'total_reach': 0,
            'total_likes': 0,
            'total_engagement': 0
        })
        for post in self.media:
            media_type = post.get('media_type', 'UNKNOWN')
            saves = self._safe_numeric(post.get('saved', 0))
            reach = self._safe_numeric(post.get('reach', 0))
            likes = self._safe_numeric(post.get('likes', 0))
            engagement = self._safe_numeric(post.get('engagement', 0))
            type_stats[media_type]['posts'].append(post)
            type_stats[media_type]['count'] += 1
            type_stats[media_type]['total_saves'] += saves
            type_stats[media_type]['total_reach'] += reach
            type_stats[media_type]['total_likes'] += likes
            type_stats[media_type]['total_engagement'] += engagement
        types_result = []
        for media_type, stats in type_stats.items():
            count = stats['count']
            avg_saves = stats['total_saves'] / count if count > 0 else 0
            avg_reach = stats['total_reach'] / count if count > 0 else 0
            avg_likes = stats['total_likes'] / count if count > 0 else 0
            avg_engagement = stats['total_engagement'] / count if count > 0 else 0
            save_rate = (stats['total_saves'] / stats['total_reach'] * 100) if stats['total_reach'] > 0 else 0
            types_result.append({
                'type': media_type,
                'count': count,
                'avg_saves': round(avg_saves, 2),
                'avg_reach': round(avg_reach, 2),
                'avg_likes': round(avg_likes, 2),
                'avg_engagement': round(avg_engagement, 2),
                'save_rate': round(save_rate, 2)
            })
        types_result.sort(key=lambda x: x['save_rate'], reverse=True)
        recommendation = self._get_content_type_recommendation(types_result)
        return {
            'success': True,
            'message': 'Content type analysis completed',
            'types': types_result,
            'recommendation': recommendation
        }
    def analyze_hashtags(self) -> List[Dict]:
        if len(self.media) < self.MIN_POSTS_HASHTAG:
            logger.warning(f"Need at least {self.MIN_POSTS_HASHTAG} posts for hashtag analysis")
            return []
        hashtag_stats = defaultdict(lambda: {
            'posts': [],
            'total_reach': 0,
            'total_saves': 0,
            'count': 0
        })
        for post in self.media:
            caption = post.get('caption', '') or ''
            hashtags = self._extract_hashtags(caption)
            reach = self._safe_numeric(post.get('reach', 0))
            saves = self._safe_numeric(post.get('saved', 0))
            for tag in hashtags:
                hashtag_stats[tag]['posts'].append(post)
                hashtag_stats[tag]['total_reach'] += reach
                hashtag_stats[tag]['total_saves'] += saves
                hashtag_stats[tag]['count'] += 1
        result = []
        for hashtag, stats in hashtag_stats.items():
            count = stats['count']
            avg_reach = stats['total_reach'] / count if count > 0 else 0
            avg_saves = stats['total_saves'] / count if count > 0 else 0
            save_rate = (stats['total_saves'] / stats['total_reach'] * 100) if stats['total_reach'] > 0 else 0
            result.append({
                'hashtag': f"#{hashtag}",
                'category': self._categorize_hashtag(hashtag),
                'posts_count': count,
                'avg_reach': int(avg_reach),
                'avg_saves': int(avg_saves),
                'save_rate': round(save_rate, 2)
            })
        result.sort(key=lambda x: x['save_rate'], reverse=True)
        return result
    def analyze_posting_patterns(self) -> Dict:
        if len(self.media) < self.MIN_POSTS_POSTING:
            return {
                'success': False,
                'message': f'Need at least {self.MIN_POSTS_POSTING} posts for posting pattern analysis',
                'best_days': [],
                'best_hours': [],
                'timezone': 'Moscow (UTC+3)',
                'recommendation': 'Collect more posts for analysis'
            }
        day_stats = defaultdict(lambda: {'saves': [], 'engagement': []})
        hour_stats = defaultdict(lambda: {'saves': [], 'engagement': []})
        for post in self.media:
            timestamp_str = post.get('timestamp')
            if not timestamp_str:
                continue
            dt = self._parse_timestamp(timestamp_str)
            if not dt:
                continue
            moscow_dt = self._get_moscow_datetime(dt)
            day_name = moscow_dt.strftime('%a')
            hour = moscow_dt.hour
            saves = self._safe_numeric(post.get('saved', 0))
            engagement = self._safe_numeric(post.get('engagement', 0))
            day_stats[day_name]['saves'].append(saves)
            day_stats[day_name]['engagement'].append(engagement)
            hour_stats[hour]['saves'].append(saves)
            hour_stats[hour]['engagement'].append(engagement)
        best_days = []
        for day, stats in day_stats.items():
            avg_saves = mean(stats['saves']) if stats['saves'] else 0
            avg_engagement = mean(stats['engagement']) if stats['engagement'] else 0
            best_days.append({
                'day': day,
                'avg_saves': int(avg_saves),
                'avg_engagement': int(avg_engagement),
                'post_count': len(stats['saves'])
            })
        best_days.sort(key=lambda x: x['avg_saves'], reverse=True)
        best_days = best_days[:3]
        best_hours = []
        for hour, stats in hour_stats.items():
            avg_saves = mean(stats['saves']) if stats['saves'] else 0
            avg_engagement = mean(stats['engagement']) if stats['engagement'] else 0
            best_hours.append({
                'hour': f"{hour:02d}:00 (MSK)",
                'avg_saves': int(avg_saves),
                'avg_engagement': int(avg_engagement),
                'post_count': len(stats['saves'])
            })
        best_hours.sort(key=lambda x: x['avg_saves'], reverse=True)
        best_hours = best_hours[:5]
        recommendation = self._get_posting_recommendation(best_days, best_hours)
        return {
            'success': True,
            'message': 'Posting pattern analysis completed',
            'best_days': best_days,
            'best_hours': best_hours,
            'timezone': 'Moscow (UTC+3)',
            'recommendation': recommendation
        }
    def analyze_captions(self) -> Dict:
        if len(self.media) < self.MIN_POSTS_CAPTION:
            return {
                'success': False,
                'message': f'Need at least {self.MIN_POSTS_CAPTION} posts for caption analysis',
                'avg_caption_length': 0,
                'avg_emoji_count': 0,
                'cta_posts_count': 0,
                'cta_avg_saves': 0,
                'non_cta_avg_saves': 0,
                'cta_effectiveness': 'insufficient_data'
            }
        caption_lengths = []
        emoji_counts = []
        cta_posts_saves = []
        non_cta_posts_saves = []
        for post in self.media:
            caption = post.get('caption', '') or ''
            saves = self._safe_numeric(post.get('saved', 0))
            caption_lengths.append(len(caption))
            emoji_count = sum(1 for char in caption if ord(char) > 0x1F300)
            emoji_counts.append(emoji_count)
            has_cta = self._has_cta(caption)
            if has_cta:
                cta_posts_saves.append(saves)
            else:
                non_cta_posts_saves.append(saves)
        avg_caption_length = mean(caption_lengths) if caption_lengths else 0
        avg_emoji_count = mean(emoji_counts) if emoji_counts else 0
        cta_avg_saves = int(mean(cta_posts_saves)) if cta_posts_saves else 0
        non_cta_avg_saves = int(mean(non_cta_posts_saves)) if non_cta_posts_saves else 0
        if cta_posts_saves and non_cta_posts_saves:
            if cta_avg_saves > non_cta_avg_saves * 1.1:
                cta_effectiveness = 'higher'
            elif cta_avg_saves < non_cta_avg_saves * 0.9:
                cta_effectiveness = 'lower'
            else:
                cta_effectiveness = 'similar'
        else:
            cta_effectiveness = 'insufficient_data'
        return {
            'success': True,
            'message': 'Caption analysis completed',
            'avg_caption_length': int(avg_caption_length),
            'avg_emoji_count': round(avg_emoji_count, 1),
            'cta_posts_count': len(cta_posts_saves),
            'non_cta_posts_count': len(non_cta_posts_saves),
            'cta_avg_saves': cta_avg_saves,
            'non_cta_avg_saves': non_cta_avg_saves,
            'cta_effectiveness': cta_effectiveness
        }
    def analyze_stories_performance(self) -> Dict:
        if not self.stories:
            return {
                'success': False,
                'message': 'No stories data available',
                'stories_analyzed': 0
            }
        total_reach = 0
        total_replies = 0
        total_impressions = 0
        total_exits = 0
        completion_rates = []
        for story in self.stories:
            reach = self._safe_numeric(story.get('reach', 0))
            replies = self._safe_numeric(story.get('replies', 0))
            impressions = self._safe_numeric(story.get('impressions', 0))
            exits = self._safe_numeric(story.get('exits', 0))
            completion_rate = self._safe_numeric(story.get('completion_rate', 0))
            total_reach += reach
            total_replies += replies
            total_impressions += impressions
            total_exits += exits
            if completion_rate > 0:
                completion_rates.append(completion_rate)
        stories_count = len(self.stories)
        avg_completion_rate = mean(completion_rates) if completion_rates else 0
        reply_rate = (total_replies / total_reach * 100) if total_reach > 0 else 0
        return {
            'success': True,
            'message': 'Stories analysis completed',
            'stories_analyzed': stories_count,
            'total_reach': total_reach,
            'total_impressions': total_impressions,
            'total_replies': total_replies,
            'total_exits': total_exits,
            'avg_completion_rate': round(avg_completion_rate, 2),
            'reply_rate': round(reply_rate, 2)
        }
    def get_full_analysis(self) -> Dict:
        analysis = {
            'posts_analyzed': len(self.media),
            'top_posts_by_saves': self.get_top_performing(metric='saves', limit=5),
            'content_types': self.analyze_content_types(),
            'hashtags': self.analyze_hashtags(),
            'posting_patterns': self.analyze_posting_patterns(),
            'captions': self.analyze_captions(),
            'stories': self.analyze_stories_performance(),
            'insights_for_fashion_brand': self._get_fashion_insights()
        }
        return analysis
    def _extract_hashtags(self, text: str) -> List[str]:
        if not text:
            return []
        pattern = r'#(\w+)'
        hashtags = re.findall(pattern, text.lower())
        return hashtags
    def _categorize_hashtag(self, tag: str) -> str:
        tag_lower = tag.lower()
        if tag_lower in self.BRAND_HASHTAGS:
            return 'brand'
        elif tag_lower in self.PRODUCT_HASHTAGS:
            return 'product'
        elif tag_lower in self.STYLE_HASHTAGS:
            return 'style'
        else:
            return 'trending'
    def _parse_timestamp(self, timestamp: str) -> Optional[datetime]:
        try:
            dt = datetime.fromisoformat(timestamp.replace('+0000', '+00:00'))
            return dt
        except (ValueError, AttributeError) as e:
            logger.warning(f"Failed to parse timestamp '{timestamp}': {e}")
            return None
    def _get_moscow_datetime(self, dt: datetime) -> datetime:
        if dt.tzinfo is None:
            dt = pytz.utc.localize(dt)
        moscow_dt = dt.astimezone(self.MOSCOW_TZ)
        return moscow_dt
    def _safe_numeric(self, value, default: float = 0.0) -> float:
        try:
            return float(value) if value is not None else default
        except (ValueError, TypeError):
            return default
    def _has_cta(self, text: str) -> bool:
        if not text:
            return False
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in self.CTA_KEYWORDS)
    def _get_content_type_recommendation(self, type_stats: List[Dict]) -> str:
        if not type_stats:
            return "Insufficient data for recommendation"
        best_type = type_stats[0]
        type_name = best_type['type']
        save_rate = best_type['save_rate']
        type_names = {
            'IMAGE': 'статичные посты (фото)',
            'VIDEO': 'Reels (видео)',
            'CAROUSEL_ALBUM': 'карусели (альбомы)'
        }
        readable_name = type_names.get(type_name, type_name)
        return (
            f"Лучший тип контента: {readable_name} "
            f"(save rate {save_rate}%). "
            f"Рекомендуем публиковать больше этого формата."
        )
    def _get_posting_recommendation(
        self,
        best_days: List[Dict],
        best_hours: List[Dict]
    ) -> str:
        if not best_days or not best_hours:
            return "Insufficient data for recommendation"
        top_day = best_days[0]['day']
        top_hour = best_hours[0]['hour']
        return (
            f"Лучшее время для публикации: {top_day} в {top_hour}. "
            f"Посты в это время имеют наибольший покупательский интерес (saves)."
        )
    def _get_fashion_insights(self) -> Dict:
        if not self.media:
            return {
                'success': False,
                'message': 'No data for insights',
                'avg_save_rate': 0,
                'save_rate_benchmark': 'insufficient_data',
                'recommendation': 'Collect more posts for analysis'
            }
        total_saves = sum(self._safe_numeric(p.get('saved', 0)) for p in self.media)
        total_reach = sum(self._safe_numeric(p.get('reach', 0)) for p in self.media)
        avg_save_rate = (total_saves / total_reach * 100) if total_reach > 0 else 0
        if avg_save_rate > 3.0:
            benchmark = 'excellent'
            benchmark_text = 'отличный (>3%)'
        elif avg_save_rate > 1.0:
            benchmark = 'good'
            benchmark_text = 'хороший (1-3%)'
        else:
            benchmark = 'poor'
            benchmark_text = 'низкий (<1%)'
        best_product = self._find_best_product_category()
        recommendation = self._generate_fashion_recommendation(
            avg_save_rate,
            benchmark,
            best_product
        )
        return {
            'success': True,
            'message': 'Fashion insights generated',
            'avg_save_rate': round(avg_save_rate, 2),
            'save_rate_benchmark': benchmark,
            'benchmark_description': benchmark_text,
            'best_performing_product': best_product,
            'recommendation': recommendation
        }
    def _find_best_product_category(self) -> str:
        product_saves = defaultdict(list)
        for post in self.media:
            caption = post.get('caption', '') or ''
            hashtags = self._extract_hashtags(caption)
            saves = self._safe_numeric(post.get('saved', 0))
            for tag in hashtags:
                if tag in self.PRODUCT_HASHTAGS:
                    product_saves[tag].append(saves)
        if not product_saves:
            return 'general'
        best_product = max(
            product_saves.items(),
            key=lambda x: mean(x[1])
        )
        return best_product[0]
    def _generate_fashion_recommendation(
        self,
        avg_save_rate: float,
        benchmark: str,
        best_product: str
    ) -> str:
        if benchmark == 'excellent':
            rec = (
                f"Отличный результат! Save rate {avg_save_rate:.1f}% показывает "
                f"высокий покупательский интерес. "
            )
        elif benchmark == 'good':
            rec = (
                f"Хороший результат. Save rate {avg_save_rate:.1f}% можно улучшить. "
            )
        else:
            rec = (
                f"Save rate {avg_save_rate:.1f}% требует внимания. "
                f"Рекомендуем усилить CTA и визуальную привлекательность контента. "
            )
        if best_product != 'general':
            rec += f"Категория '{best_product}' показывает лучшие результаты - делайте больше такого контента."
        return rec
