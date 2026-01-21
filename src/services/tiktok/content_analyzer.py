from __future__ import annotations
import re
from collections import defaultdict, Counter
from datetime import datetime
from statistics import mean
from typing import Dict, List, Optional, Tuple
class TikTokContentAnalyzer:
    MIN_VIDEOS_HASHTAG = 3
    MIN_VIDEOS_POSTING = 5
    MIN_VIDEOS_DURATION = 3
    MIN_VIDEOS_VIRAL = 4
    MIN_VIDEOS_TREND = 8
    DURATION_BUCKETS: List[Tuple[int, float, str]] = [
        (0, 15, "0-15s"),
        (15, 30, "15-30s"),
        (30, 60, "30-60s"),
        (60, 180, "1-3min"),
        (180, float('inf'), "3min+")
    ]
    TREND_RISING_THRESHOLD = 1.2
    TREND_DECLINING_THRESHOLD = 0.8
    DAY_NAMES = {
        0: 'Понедельник',
        1: 'Вторник',
        2: 'Среда',
        3: 'Четверг',
        4: 'Пятница',
        5: 'Суббота',
        6: 'Воскресенье'
    }
    def __init__(self, videos: Optional[List[Dict]] = None):
        self.videos = videos or []
        self._validate_videos()
    def _validate_videos(self) -> None:
        if not self.videos:
            return
        valid_videos = []
        required_fields = ['video_id', 'title', 'views', 'engagement_rate']
        for video in self.videos:
            if all(field in video for field in required_fields):
                valid_videos.append(video)
        self.videos = valid_videos
    def analyze_hashtags(self) -> Dict:
        if len(self.videos) < self.MIN_VIDEOS_HASHTAG:
            return {
                'success': False,
                'message': f'Недостаточно видео для анализа хэштегов (минимум {self.MIN_VIDEOS_HASHTAG})',
                'hashtags': [],
                'total_unique_hashtags': 0,
                'videos_with_hashtags': 0,
                'videos_without_hashtags': 0
            }
        hashtag_data = defaultdict(lambda: {'videos': [], 'views': [], 'engagement': []})
        videos_with_hashtags = 0
        for video in self.videos:
            title = video.get('title', '')
            hashtags = self._extract_hashtags(title)
            if hashtags:
                videos_with_hashtags += 1
            for hashtag in hashtags:
                hashtag_data[hashtag]['videos'].append(video)
                hashtag_data[hashtag]['views'].append(self._safe_numeric(video.get('views', 0)))
                hashtag_data[hashtag]['engagement'].append(self._safe_numeric(video.get('engagement_rate', 0)))
        if not hashtag_data:
            return {
                'success': False,
                'message': 'Хэштеги не найдены в заголовках видео. Рекомендуется использовать хэштеги для лучшей видимости.',
                'hashtags': [],
                'total_unique_hashtags': 0,
                'videos_with_hashtags': 0,
                'videos_without_hashtags': len(self.videos)
            }
        hashtag_results = []
        for hashtag, data in hashtag_data.items():
            count = len(data['videos'])
            avg_views = mean(data['views'])
            avg_engagement = mean(data['engagement'])
            trend = self._calculate_hashtag_trend(hashtag, data['videos'])
            hashtag_results.append({
                'hashtag': hashtag,
                'count': count,
                'avg_views': avg_views,
                'avg_engagement': avg_engagement,
                'trend': trend
            })
        hashtag_results.sort(key=lambda x: x['count'], reverse=True)
        return {
            'success': True,
            'message': f'Найдено {len(hashtag_results)} уникальных хэштегов',
            'hashtags': hashtag_results,
            'total_unique_hashtags': len(hashtag_results),
            'videos_with_hashtags': videos_with_hashtags,
            'videos_without_hashtags': len(self.videos) - videos_with_hashtags
        }
    def analyze_posting_patterns(self) -> Dict:
        if len(self.videos) < self.MIN_VIDEOS_POSTING:
            return {
                'success': False,
                'message': f'Недостаточно видео для анализа времени публикации (минимум {self.MIN_VIDEOS_POSTING})',
                'best_days': [],
                'best_hours': [],
                'optimal_frequency': 'N/A'
            }
        day_data = defaultdict(lambda: {'engagement': [], 'count': 0})
        hour_data = defaultdict(lambda: {'engagement': [], 'count': 0})
        parsed_dates = []
        for video in self.videos:
            dt = self._parse_published_at(video.get('published_at'))
            if not dt:
                continue
            parsed_dates.append(dt)
            engagement = self._safe_numeric(video.get('engagement_rate', 0))
            day = dt.weekday()
            day_data[day]['engagement'].append(engagement)
            day_data[day]['count'] += 1
            hour = dt.hour
            hour_data[hour]['engagement'].append(engagement)
            hour_data[hour]['count'] += 1
        if not parsed_dates:
            return {
                'success': False,
                'message': 'Не удалось распарсить даты публикации видео',
                'best_days': [],
                'best_hours': [],
                'optimal_frequency': 'N/A'
            }
        best_days = []
        for day, data in day_data.items():
            if data['engagement']:
                best_days.append({
                    'day': self.DAY_NAMES[day],
                    'avg_engagement': mean(data['engagement']),
                    'video_count': data['count']
                })
        best_days.sort(key=lambda x: x['avg_engagement'], reverse=True)
        best_hours = []
        for hour, data in hour_data.items():
            if data['engagement']:
                best_hours.append({
                    'hour': hour,
                    'avg_engagement': mean(data['engagement']),
                    'video_count': data['count']
                })
        best_hours.sort(key=lambda x: x['avg_engagement'], reverse=True)
        if len(parsed_dates) >= 2:
            date_range = (max(parsed_dates) - min(parsed_dates)).days
            if date_range > 0:
                videos_per_week = (len(parsed_dates) / date_range) * 7
                optimal_frequency = f"{videos_per_week:.1f} видео в неделю"
            else:
                optimal_frequency = "Все видео опубликованы в один день"
        else:
            optimal_frequency = "Недостаточно данных"
        return {
            'success': True,
            'message': f'Проанализировано {len(parsed_dates)} видео',
            'best_days': best_days,
            'best_hours': best_hours,
            'optimal_frequency': optimal_frequency
        }
    def analyze_video_duration(self) -> Dict:
        if len(self.videos) < self.MIN_VIDEOS_DURATION:
            return {
                'success': False,
                'message': f'Недостаточно видео для анализа длительности (минимум {self.MIN_VIDEOS_DURATION})',
                'duration_buckets': [],
                'optimal_duration': 'N/A'
            }
        bucket_data = defaultdict(lambda: {'videos': [], 'views': [], 'engagement': []})
        for video in self.videos:
            duration = self._safe_numeric(video.get('duration', 0))
            bucket = self._get_duration_bucket(int(duration))
            if bucket:
                bucket_data[bucket]['videos'].append(video)
                bucket_data[bucket]['views'].append(self._safe_numeric(video.get('views', 0)))
                bucket_data[bucket]['engagement'].append(self._safe_numeric(video.get('engagement_rate', 0)))
        if not bucket_data:
            return {
                'success': False,
                'message': 'Не удалось определить длительность видео',
                'duration_buckets': [],
                'optimal_duration': 'N/A'
            }
        bucket_results = []
        for bucket, data in bucket_data.items():
            if data['views']:
                bucket_results.append({
                    'bucket': bucket,
                    'video_count': len(data['videos']),
                    'avg_views': mean(data['views']),
                    'avg_engagement': mean(data['engagement'])
                })
        bucket_results.sort(key=lambda x: x['avg_engagement'], reverse=True)
        if bucket_results:
            optimal_duration = bucket_results[0]['bucket']
        else:
            optimal_duration = 'N/A'
        if len(bucket_results) == 1:
            message = f'Все видео в диапазоне {optimal_duration}'
        else:
            message = f'Найдено {len(bucket_results)} диапазонов длительности'
        return {
            'success': True,
            'message': message,
            'duration_buckets': bucket_results,
            'optimal_duration': optimal_duration
        }
    def detect_viral_content(self, threshold_multiplier: float = 3.0) -> Dict:
        if len(self.videos) < self.MIN_VIDEOS_VIRAL:
            return {
                'success': False,
                'message': f'Недостаточно видео для определения вирусного контента (минимум {self.MIN_VIDEOS_VIRAL})',
                'threshold_views': 0,
                'viral_videos': [],
                'viral_rate': 0.0
            }
        all_views = [self._safe_numeric(v.get('views', 0)) for v in self.videos]
        avg_views = mean(all_views) if all_views else 0
        threshold_views = avg_views * threshold_multiplier
        viral_videos = []
        for video in self.videos:
            views = self._safe_numeric(video.get('views', 0))
            if views >= threshold_views:
                viral_videos.append({
                    'video_id': video.get('video_id', ''),
                    'title': video.get('title', 'Untitled'),
                    'views': int(views),
                    'engagement_rate': self._safe_numeric(video.get('engagement_rate', 0)),
                    'multiplier': views / avg_views if avg_views > 0 else 0,
                    'published_at': video.get('published_at', '')
                })
        viral_videos.sort(key=lambda x: x['views'], reverse=True)
        viral_rate = (len(viral_videos) / len(self.videos)) * 100 if self.videos else 0
        message = f'Найдено {len(viral_videos)} вирусных видео ({viral_rate:.1f}%)'
        return {
            'success': True,
            'message': message,
            'threshold_views': threshold_views,
            'viral_videos': viral_videos,
            'viral_rate': viral_rate
        }
    def _safe_numeric(self, value, default: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default
    def _extract_hashtags(self, text: str) -> List[str]:
        if not text:
            return []
        hashtags = re.findall(r'#(\w+)', text)
        return [h.lower() for h in hashtags]
    def _calculate_hashtag_trend(self, hashtag: str, videos: List[Dict]) -> str:
        if len(videos) < self.MIN_VIDEOS_TREND:
            return 'insufficient_data'
        sorted_videos = sorted(
            videos,
            key=lambda v: self._parse_published_at(v.get('published_at')) or datetime.min
        )
        mid = len(sorted_videos) // 2
        older_videos = sorted_videos[:mid]
        recent_videos = sorted_videos[mid:]
        older_engagement = [self._safe_numeric(v.get('engagement_rate', 0)) for v in older_videos]
        recent_engagement = [self._safe_numeric(v.get('engagement_rate', 0)) for v in recent_videos]
        if not older_engagement or not recent_engagement:
            return 'insufficient_data'
        avg_older = mean(older_engagement) if older_engagement else 0
        avg_recent = mean(recent_engagement) if recent_engagement else 0
        if avg_older == 0:
            return 'insufficient_data'
        ratio = avg_recent / avg_older
        if ratio >= self.TREND_RISING_THRESHOLD:
            return 'rising'
        elif ratio <= self.TREND_DECLINING_THRESHOLD:
            return 'declining'
        else:
            return 'stable'
    def _get_duration_bucket(self, duration: int) -> Optional[str]:
        if duration < 0:
            return None
        for min_dur, max_dur, label in self.DURATION_BUCKETS:
            if min_dur <= duration < max_dur:
                return label
        return None
    def _parse_published_at(self, published_at: Optional[str]) -> Optional[datetime]:
        if not published_at:
            return None
        try:
            if '.' in published_at:
                return datetime.fromisoformat(published_at.replace('Z', '+00:00'))
            else:
                return datetime.fromisoformat(published_at.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            return None
