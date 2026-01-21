import pytest
from datetime import datetime, timedelta
from src.services.tiktok.content_analyzer import TikTokContentAnalyzer
@pytest.fixture
def sample_videos():
    base_date = datetime(2024, 1, 1, 12, 0, 0)
    return [
        {
            'video_id': 'video1',
            'title': 'Check out my new outfit #fashion #ootd #style',
            'published_at': base_date.isoformat(),
            'views': 10000,
            'likes': 800,
            'comments': 50,
            'shares': 30,
            'duration': 25,
            'engagement_rate': 8.8
        },
        {
            'video_id': 'video2',
            'title': 'Summer collection is here! #summer #fashion',
            'published_at': (base_date + timedelta(days=2)).isoformat(),
            'views': 15000,
            'likes': 1200,
            'comments': 80,
            'shares': 40,
            'duration': 45,
            'engagement_rate': 8.8
        },
        {
            'video_id': 'video3',
            'title': 'Winter sale announcement #sale #fashion',
            'published_at': (base_date + timedelta(days=4)).isoformat(),
            'views': 5000,
            'likes': 300,
            'comments': 20,
            'shares': 10,
            'duration': 12,
            'engagement_rate': 6.6
        },
        {
            'video_id': 'video4',
            'title': 'Behind the scenes #bts',
            'published_at': (base_date + timedelta(days=6, hours=3)).isoformat(),
            'views': 8000,
            'likes': 600,
            'comments': 40,
            'shares': 20,
            'duration': 90,
            'engagement_rate': 8.25
        },
        {
            'video_id': 'video5',
            'title': 'New arrivals showcase #fashion #newarrival',
            'published_at': (base_date + timedelta(days=8, hours=-2)).isoformat(),
            'views': 12000,
            'likes': 1000,
            'comments': 60,
            'shares': 35,
            'duration': 35,
            'engagement_rate': 9.125
        }
    ]
@pytest.fixture
def viral_videos():
    base_date = datetime(2024, 1, 1, 12, 0, 0)
    return [
        {
            'video_id': 'normal1',
            'title': 'Regular post #fashion',
            'published_at': base_date.isoformat(),
            'views': 5000,
            'likes': 400,
            'comments': 20,
            'shares': 10,
            'duration': 30,
            'engagement_rate': 8.6
        },
        {
            'video_id': 'normal2',
            'title': 'Another post #style',
            'published_at': (base_date + timedelta(days=1)).isoformat(),
            'views': 6000,
            'likes': 480,
            'comments': 25,
            'shares': 15,
            'duration': 25,
            'engagement_rate': 8.67
        },
        {
            'video_id': 'normal3',
            'title': 'Daily content #ootd',
            'published_at': (base_date + timedelta(days=2)).isoformat(),
            'views': 5500,
            'likes': 440,
            'comments': 22,
            'shares': 12,
            'duration': 28,
            'engagement_rate': 8.62
        },
        {
            'video_id': 'viral1',
            'title': 'VIRAL HIT #trending #fashion',
            'published_at': (base_date + timedelta(days=3)).isoformat(),
            'views': 50000,
            'likes': 4000,
            'comments': 200,
            'shares': 150,
            'duration': 32,
            'engagement_rate': 8.7
        }
    ]
class TestHashtagAnalysis:
    def test_extract_hashtags_from_title(self):
        analyzer = TikTokContentAnalyzer([])
        hashtags = analyzer._extract_hashtags("#fashion #style #ootd")
        assert set(hashtags) == {'fashion', 'style', 'ootd'}
        hashtags = analyzer._extract_hashtags("#Fashion #STYLE #OotD")
        assert set(hashtags) == {'fashion', 'style', 'ootd'}
        hashtags = analyzer._extract_hashtags("Check this out #fashion and #style!")
        assert set(hashtags) == {'fashion', 'style'}
        hashtags = analyzer._extract_hashtags("No hashtags here")
        assert hashtags == []
        hashtags = analyzer._extract_hashtags("")
        assert hashtags == []
        hashtags = analyzer._extract_hashtags(None)
        assert hashtags == []
    def test_hashtag_analysis_insufficient_data(self):
        videos = [
            {'video_id': '1', 'title': '#test', 'views': 100, 'engagement_rate': 5.0},
            {'video_id': '2', 'title': '#test', 'views': 200, 'engagement_rate': 6.0}
        ]
        analyzer = TikTokContentAnalyzer(videos)
        result = analyzer.analyze_hashtags()
        assert result['success'] is False
        assert 'Недостаточно видео' in result['message']
        assert result['hashtags'] == []
    def test_hashtag_analysis_success(self, sample_videos):
        analyzer = TikTokContentAnalyzer(sample_videos)
        result = analyzer.analyze_hashtags()
        assert result['success'] is True
        assert len(result['hashtags']) > 0
        assert result['total_unique_hashtags'] > 0
        assert result['videos_with_hashtags'] >= 0
        hashtag = result['hashtags'][0]
        assert 'hashtag' in hashtag
        assert 'count' in hashtag
        assert 'avg_views' in hashtag
        assert 'avg_engagement' in hashtag
        assert 'trend' in hashtag
        fashion_hashtag = next((h for h in result['hashtags'] if h['hashtag'] == 'fashion'), None)
        assert fashion_hashtag is not None
        assert fashion_hashtag['count'] >= 3
    def test_hashtag_trend_detection(self):
        base_date = datetime(2024, 1, 1, 12, 0, 0)
        videos = []
        for i in range(8):
            videos.append({
                'video_id': f'vid{i}',
                'title': f'Post {i} #trending',
                'published_at': (base_date + timedelta(days=i)).isoformat(),
                'views': 5000 + (i * 500),
                'likes': 400 + (i * 50),
                'comments': 20,
                'shares': 10,
                'duration': 30,
                'engagement_rate': 5.0 + (i * 0.5)
            })
        analyzer = TikTokContentAnalyzer(videos)
        result = analyzer.analyze_hashtags()
        assert result['success'] is True
        trending = next((h for h in result['hashtags'] if h['hashtag'] == 'trending'), None)
        assert trending is not None
        assert trending['trend'] == 'rising'
    def test_no_hashtags_found(self):
        videos = [
            {'video_id': '1', 'title': 'No hashtags', 'views': 100, 'engagement_rate': 5.0},
            {'video_id': '2', 'title': 'Also no hashtags', 'views': 200, 'engagement_rate': 6.0},
            {'video_id': '3', 'title': 'Still none', 'views': 150, 'engagement_rate': 5.5}
        ]
        analyzer = TikTokContentAnalyzer(videos)
        result = analyzer.analyze_hashtags()
        assert result['success'] is False
        assert 'не найдены' in result['message'].lower()
        assert result['videos_without_hashtags'] == 3
class TestPostingPatterns:
    def test_posting_patterns_insufficient_data(self):
        videos = [
            {'video_id': '1', 'title': 'Test', 'published_at': datetime.now().isoformat(),
             'views': 100, 'engagement_rate': 5.0}
        ]
        analyzer = TikTokContentAnalyzer(videos)
        result = analyzer.analyze_posting_patterns()
        assert result['success'] is False
        assert 'Недостаточно видео' in result['message']
    def test_posting_patterns_by_day(self, sample_videos):
        analyzer = TikTokContentAnalyzer(sample_videos)
        result = analyzer.analyze_posting_patterns()
        assert result['success'] is True
        assert len(result['best_days']) > 0
        day = result['best_days'][0]
        assert 'day' in day
        assert 'avg_engagement' in day
        assert 'video_count' in day
        assert any(day['day'] in TikTokContentAnalyzer.DAY_NAMES.values() for day in result['best_days'])
    def test_posting_patterns_by_hour(self, sample_videos):
        analyzer = TikTokContentAnalyzer(sample_videos)
        result = analyzer.analyze_posting_patterns()
        assert result['success'] is True
        assert len(result['best_hours']) > 0
        hour = result['best_hours'][0]
        assert 'hour' in hour
        assert 'avg_engagement' in hour
        assert 'video_count' in hour
        assert 0 <= hour['hour'] <= 23
    def test_optimal_frequency_calculation(self, sample_videos):
        analyzer = TikTokContentAnalyzer(sample_videos)
        result = analyzer.analyze_posting_patterns()
        assert result['success'] is True
        assert 'optimal_frequency' in result
        assert 'видео в неделю' in result['optimal_frequency']
    def test_invalid_dates(self):
        videos = [
            {'video_id': '1', 'title': 'Test', 'published_at': 'invalid_date',
             'views': 100, 'engagement_rate': 5.0},
            {'video_id': '2', 'title': 'Test', 'published_at': None,
             'views': 200, 'engagement_rate': 6.0},
            {'video_id': '3', 'title': 'Test', 'published_at': '',
             'views': 150, 'engagement_rate': 5.5},
            {'video_id': '4', 'title': 'Test', 'published_at': '',
             'views': 150, 'engagement_rate': 5.5},
            {'video_id': '5', 'title': 'Test', 'published_at': '',
             'views': 150, 'engagement_rate': 5.5}
        ]
        analyzer = TikTokContentAnalyzer(videos)
        result = analyzer.analyze_posting_patterns()
        assert result['success'] is False
class TestDurationAnalysis:
    def test_duration_bucketing(self):
        analyzer = TikTokContentAnalyzer([])
        assert analyzer._get_duration_bucket(10) == "0-15s"
        assert analyzer._get_duration_bucket(20) == "15-30s"
        assert analyzer._get_duration_bucket(45) == "30-60s"
        assert analyzer._get_duration_bucket(120) == "1-3min"
        assert analyzer._get_duration_bucket(200) == "3min+"
        assert analyzer._get_duration_bucket(0) == "0-15s"
        assert analyzer._get_duration_bucket(15) == "15-30s"
        assert analyzer._get_duration_bucket(30) == "30-60s"
        assert analyzer._get_duration_bucket(60) == "1-3min"
        assert analyzer._get_duration_bucket(180) == "3min+"
        assert analyzer._get_duration_bucket(-10) is None
    def test_duration_analysis_success(self, sample_videos):
        analyzer = TikTokContentAnalyzer(sample_videos)
        result = analyzer.analyze_video_duration()
        assert result['success'] is True
        assert len(result['duration_buckets']) > 0
        assert result['optimal_duration'] != 'N/A'
        bucket = result['duration_buckets'][0]
        assert 'bucket' in bucket
        assert 'video_count' in bucket
        assert 'avg_views' in bucket
        assert 'avg_engagement' in bucket
    def test_duration_insufficient_data(self):
        videos = [
            {'video_id': '1', 'title': 'Test', 'duration': 30, 'views': 100, 'engagement_rate': 5.0}
        ]
        analyzer = TikTokContentAnalyzer(videos)
        result = analyzer.analyze_video_duration()
        assert result['success'] is False
        assert 'Недостаточно видео' in result['message']
    def test_all_same_duration(self):
        videos = [
            {'video_id': '1', 'title': 'Test', 'duration': 25, 'views': 100, 'engagement_rate': 5.0},
            {'video_id': '2', 'title': 'Test', 'duration': 28, 'views': 200, 'engagement_rate': 6.0},
            {'video_id': '3', 'title': 'Test', 'duration': 27, 'views': 150, 'engagement_rate': 5.5}
        ]
        analyzer = TikTokContentAnalyzer(videos)
        result = analyzer.analyze_video_duration()
        assert result['success'] is True
        assert len(result['duration_buckets']) == 1
        assert 'Все видео в диапазоне' in result['message']
class TestViralDetection:
    def test_viral_detection_insufficient_data(self):
        videos = [
            {'video_id': '1', 'title': 'Test', 'views': 100, 'engagement_rate': 5.0}
        ]
        analyzer = TikTokContentAnalyzer(videos)
        result = analyzer.detect_viral_content()
        assert result['success'] is False
        assert 'Недостаточно видео' in result['message']
    def test_viral_detection_with_threshold(self, viral_videos):
        analyzer = TikTokContentAnalyzer(viral_videos)
        result = analyzer.detect_viral_content(threshold_multiplier=3.0)
        assert result['success'] is True
        assert len(result['viral_videos']) >= 1
        assert result['threshold_views'] > 0
        if result['viral_videos']:
            viral = result['viral_videos'][0]
            assert 'video_id' in viral
            assert 'title' in viral
            assert 'views' in viral
            assert 'engagement_rate' in viral
            assert 'multiplier' in viral
            assert viral['views'] >= result['threshold_views']
    def test_viral_rate_calculation(self, viral_videos):
        analyzer = TikTokContentAnalyzer(viral_videos)
        result = analyzer.detect_viral_content(threshold_multiplier=3.0)
        assert result['success'] is True
        assert 0 <= result['viral_rate'] <= 100
    def test_no_viral_content(self):
        videos = [
            {'video_id': '1', 'title': 'Test', 'views': 1000, 'engagement_rate': 5.0},
            {'video_id': '2', 'title': 'Test', 'views': 1100, 'engagement_rate': 5.5},
            {'video_id': '3', 'title': 'Test', 'views': 1050, 'engagement_rate': 5.2},
            {'video_id': '4', 'title': 'Test', 'views': 1080, 'engagement_rate': 5.3}
        ]
        analyzer = TikTokContentAnalyzer(videos)
        result = analyzer.detect_viral_content(threshold_multiplier=3.0)
        assert result['success'] is True
        assert len(result['viral_videos']) == 0
        assert result['viral_rate'] == 0.0
    def test_custom_threshold_multiplier(self, viral_videos):
        analyzer = TikTokContentAnalyzer(viral_videos)
        result_low = analyzer.detect_viral_content(threshold_multiplier=1.5)
        result_high = analyzer.detect_viral_content(threshold_multiplier=5.0)
        assert result_low['success'] is True
        assert result_high['success'] is True
        assert len(result_low['viral_videos']) >= len(result_high['viral_videos'])
class TestEdgeCases:
    def test_empty_videos_list(self):
        analyzer = TikTokContentAnalyzer([])
        assert analyzer.analyze_hashtags()['success'] is False
        assert analyzer.analyze_posting_patterns()['success'] is False
        assert analyzer.analyze_video_duration()['success'] is False
        assert analyzer.detect_viral_content()['success'] is False
    def test_none_videos_list(self):
        analyzer = TikTokContentAnalyzer(None)
        assert len(analyzer.videos) == 0
        assert analyzer.analyze_hashtags()['success'] is False
    def test_missing_fields(self):
        videos = [
            {'video_id': '1'},
            {'title': 'Test'},
            {'video_id': '3', 'title': 'Complete', 'views': 100, 'engagement_rate': 5.0}
        ]
        analyzer = TikTokContentAnalyzer(videos)
        assert len(analyzer.videos) == 1
    def test_single_video(self):
        videos = [
            {'video_id': '1', 'title': '#test', 'views': 1000, 'engagement_rate': 5.0,
             'duration': 30, 'published_at': datetime.now().isoformat()}
        ]
        analyzer = TikTokContentAnalyzer(videos)
        assert analyzer.analyze_hashtags()['success'] is False
        assert analyzer.analyze_posting_patterns()['success'] is False
        assert analyzer.analyze_video_duration()['success'] is False
        assert analyzer.detect_viral_content()['success'] is False
    def test_malformed_data_types(self):
        videos = [
            {'video_id': '1', 'title': '#test', 'views': 'not_a_number',
             'engagement_rate': None, 'duration': 30},
            {'video_id': '2', 'title': None, 'views': 100,
             'engagement_rate': 5.0, 'duration': 'invalid'},
            {'video_id': '3', 'title': '#valid', 'views': 200,
             'engagement_rate': 6.0, 'duration': 40}
        ]
        analyzer = TikTokContentAnalyzer(videos)
        result = analyzer.analyze_hashtags()
        assert isinstance(result, dict)
        assert 'success' in result
