import pytest
from datetime import datetime
from src.services.instagram.content_analyzer import InstagramContentAnalyzer
@pytest.fixture
def sample_media():
    return [
        {
            "media_id": "1",
            "caption": "Новое платье в наличии! 👗 #dress #niginart #fashion #ootd",
            "media_type": "IMAGE",
            "timestamp": "2024-01-15T18:00:00+0000",
            "likes": 150,
            "comments": 25,
            "impressions": 5000,
            "reach": 4200,
            "saved": 180,
            "engagement": 355,
            "engagement_rate": 7.1
        },
        {
            "media_id": "2",
            "caption": "Новая коллекция юбок 💃 #skirt #стиль #мода",
            "media_type": "VIDEO",
            "timestamp": "2024-01-14T12:00:00+0000",
            "likes": 200,
            "comments": 30,
            "impressions": 8000,
            "reach": 7000,
            "saved": 210,
            "engagement": 440,
            "engagement_rate": 6.3
        },
        {
            "media_id": "3",
            "caption": "Элегантная блуза для офиса ссылка в био #blouse #офис",
            "media_type": "CAROUSEL_ALBUM",
            "timestamp": "2024-01-13T14:30:00+0000",
            "likes": 120,
            "comments": 15,
            "impressions": 4000,
            "reach": 3500,
            "saved": 100,
            "engagement": 235,
            "engagement_rate": 6.7
        },
        {
            "media_id": "4",
            "caption": "Casual look 🌟 #ootd #образ",
            "media_type": "IMAGE",
            "timestamp": "2024-01-12T10:00:00+0000",
            "likes": 90,
            "comments": 10,
            "impressions": 3000,
            "reach": 2800,
            "saved": 50,
            "engagement": 150,
            "engagement_rate": 5.4
        },
        {
            "media_id": "5",
            "caption": "Weekend vibes #weekend",
            "media_type": "VIDEO",
            "timestamp": "2024-01-11T16:00:00+0000",
            "likes": 80,
            "comments": 8,
            "impressions": 2500,
            "reach": 2300,
            "saved": 30,
            "engagement": 118,
            "engagement_rate": 5.1
        }
    ]
@pytest.fixture
def sample_stories():
    return [
        {
            "story_id": "story1",
            "reach": 1000,
            "impressions": 1200,
            "replies": 15,
            "exits": 50,
            "completion_rate": 85.0
        },
        {
            "story_id": "story2",
            "reach": 1500,
            "impressions": 1800,
            "replies": 20,
            "exits": 80,
            "completion_rate": 90.0
        }
    ]
class TestTopPerforming:
    def test_top_by_saves(self, sample_media):
        analyzer = InstagramContentAnalyzer(media=sample_media)
        top = analyzer.get_top_performing(metric="saves", limit=3)
        assert len(top) == 3
        assert top[0]["media_id"] == "2"
        assert top[1]["media_id"] == "1"
        assert top[2]["media_id"] == "3"
        assert top[0]["saved"] >= top[1]["saved"]
        assert top[1]["saved"] >= top[2]["saved"]
    def test_top_by_reach(self, sample_media):
        analyzer = InstagramContentAnalyzer(media=sample_media)
        top = analyzer.get_top_performing(metric="reach", limit=3)
        assert len(top) == 3
        assert top[0]["media_id"] == "2"
        assert top[0]["reach"] >= top[1]["reach"]
    def test_top_with_limit(self, sample_media):
        analyzer = InstagramContentAnalyzer(media=sample_media)
        top = analyzer.get_top_performing(metric="saves", limit=2)
        assert len(top) == 2
    def test_top_with_empty_media(self):
        analyzer = InstagramContentAnalyzer(media=[])
        top = analyzer.get_top_performing(metric="saves", limit=10)
        assert len(top) == 0
class TestContentTypes:
    def test_content_type_analysis(self, sample_media):
        analyzer = InstagramContentAnalyzer(media=sample_media)
        result = analyzer.analyze_content_types()
        assert result['success'] is True
        assert 'types' in result
        assert 'recommendation' in result
        assert len(result['types']) > 0
    def test_content_type_metrics(self, sample_media):
        analyzer = InstagramContentAnalyzer(media=sample_media)
        result = analyzer.analyze_content_types()
        types = result['types']
        for type_stat in types:
            assert 'type' in type_stat
            assert 'count' in type_stat
            assert 'avg_saves' in type_stat
            assert 'avg_reach' in type_stat
            assert 'save_rate' in type_stat
            assert type_stat['count'] > 0
    def test_content_type_sorting(self, sample_media):
        analyzer = InstagramContentAnalyzer(media=sample_media)
        result = analyzer.analyze_content_types()
        types = result['types']
        if len(types) > 1:
            for i in range(len(types) - 1):
                assert types[i]['save_rate'] >= types[i + 1]['save_rate']
    def test_insufficient_data(self):
        analyzer = InstagramContentAnalyzer(media=[{"media_id": "1"}])
        result = analyzer.analyze_content_types()
        assert result['success'] is False
        assert 'message' in result
        assert result['types'] == []
class TestHashtags:
    def test_hashtag_extraction(self, sample_media):
        analyzer = InstagramContentAnalyzer(media=sample_media)
        result = analyzer.analyze_hashtags()
        assert isinstance(result, list)
        assert len(result) > 0
        assert all('hashtag' in h for h in result)
        assert all(h['hashtag'].startswith('#') for h in result)
    def test_hashtag_metrics(self, sample_media):
        analyzer = InstagramContentAnalyzer(media=sample_media)
        result = analyzer.analyze_hashtags()
        for hashtag in result:
            assert 'hashtag' in hashtag
            assert 'category' in hashtag
            assert 'posts_count' in hashtag
            assert 'avg_reach' in hashtag
            assert 'avg_saves' in hashtag
            assert 'save_rate' in hashtag
            assert hashtag['posts_count'] > 0
    def test_hashtag_categorization(self):
        analyzer = InstagramContentAnalyzer(media=[])
        assert analyzer._categorize_hashtag("niginart") == "brand"
        assert analyzer._categorize_hashtag("нигинарт") == "brand"
        assert analyzer._categorize_hashtag("dress") == "product"
        assert analyzer._categorize_hashtag("платье") == "product"
        assert analyzer._categorize_hashtag("ootd") == "style"
        assert analyzer._categorize_hashtag("мода") == "style"
        assert analyzer._categorize_hashtag("random") == "trending"
    def test_hashtag_sorting(self, sample_media):
        analyzer = InstagramContentAnalyzer(media=sample_media)
        result = analyzer.analyze_hashtags()
        if len(result) > 1:
            for i in range(len(result) - 1):
                assert result[i]['save_rate'] >= result[i + 1]['save_rate']
    def test_hashtag_extraction_helper(self):
        analyzer = InstagramContentAnalyzer(media=[])
        text = "Test #fashion #style #OOTD #мода"
        hashtags = analyzer._extract_hashtags(text)
        assert len(hashtags) == 4
        assert "fashion" in hashtags
        assert "style" in hashtags
        assert "ootd" in hashtags
        assert "мода" in hashtags
    def test_empty_media_hashtags(self):
        analyzer = InstagramContentAnalyzer(media=[])
        result = analyzer.analyze_hashtags()
        assert len(result) == 0
class TestPostingPatterns:
    def test_posting_patterns_analysis(self, sample_media):
        analyzer = InstagramContentAnalyzer(media=sample_media)
        result = analyzer.analyze_posting_patterns()
        assert result['success'] is True
        assert 'best_days' in result
        assert 'best_hours' in result
        assert 'timezone' in result
        assert 'recommendation' in result
        assert result['timezone'] == 'Moscow (UTC+3)'
    def test_best_days_format(self, sample_media):
        analyzer = InstagramContentAnalyzer(media=sample_media)
        result = analyzer.analyze_posting_patterns()
        best_days = result['best_days']
        assert len(best_days) <= 3
        for day in best_days:
            assert 'day' in day
            assert 'avg_saves' in day
            assert 'avg_engagement' in day
            assert 'post_count' in day
    def test_best_hours_format(self, sample_media):
        analyzer = InstagramContentAnalyzer(media=sample_media)
        result = analyzer.analyze_posting_patterns()
        best_hours = result['best_hours']
        assert len(best_hours) <= 5
        for hour in best_hours:
            assert 'hour' in hour
            assert 'avg_saves' in hour
            assert 'avg_engagement' in hour
            assert 'post_count' in hour
            assert '(MSK)' in hour['hour']
    def test_moscow_timezone_conversion(self):
        analyzer = InstagramContentAnalyzer(media=[])
        dt = datetime(2024, 1, 15, 15, 0, 0)
        moscow_dt = analyzer._get_moscow_datetime(dt)
        assert moscow_dt.hour == 18
    def test_timestamp_parsing(self):
        analyzer = InstagramContentAnalyzer(media=[])
        timestamp = "2024-01-15T18:00:00+0000"
        dt = analyzer._parse_timestamp(timestamp)
        assert dt is not None
        assert dt.year == 2024
        assert dt.month == 1
        assert dt.day == 15
        assert dt.hour == 18
    def test_insufficient_posts_for_patterns(self):
        analyzer = InstagramContentAnalyzer(media=[{"media_id": "1"}])
        result = analyzer.analyze_posting_patterns()
        assert result['success'] is False
        assert result['best_days'] == []
        assert result['best_hours'] == []
class TestCaptions:
    def test_caption_analysis(self, sample_media):
        analyzer = InstagramContentAnalyzer(media=sample_media)
        result = analyzer.analyze_captions()
        assert result['success'] is True
        assert 'avg_caption_length' in result
        assert 'avg_emoji_count' in result
        assert 'cta_posts_count' in result
        assert 'cta_avg_saves' in result
        assert 'non_cta_avg_saves' in result
        assert 'cta_effectiveness' in result
    def test_cta_detection_russian(self):
        analyzer = InstagramContentAnalyzer(media=[])
        assert analyzer._has_cta("Новое платье ссылка в био")
        assert analyzer._has_cta("Заказать можно в директ")
        assert analyzer._has_cta("В наличии несколько размеров")
        assert analyzer._has_cta("Пиши в директ для заказа")
    def test_cta_detection_english(self):
        analyzer = InstagramContentAnalyzer(media=[])
        assert analyzer._has_cta("New dress link in bio")
        assert analyzer._has_cta("DM to order")
        assert analyzer._has_cta("Shop now")
        assert analyzer._has_cta("Available now")
    def test_no_cta(self):
        analyzer = InstagramContentAnalyzer(media=[])
        assert not analyzer._has_cta("Beautiful dress #fashion")
        assert not analyzer._has_cta("Weekend vibes")
    def test_cta_effectiveness_calculation(self, sample_media):
        analyzer = InstagramContentAnalyzer(media=sample_media)
        result = analyzer.analyze_captions()
        assert result['cta_posts_count'] > 0
        assert result['non_cta_posts_count'] > 0
        assert result['cta_effectiveness'] in ['higher', 'lower', 'similar']
    def test_insufficient_captions(self):
        analyzer = InstagramContentAnalyzer(media=[{"media_id": "1"}])
        result = analyzer.analyze_captions()
        assert result['success'] is False
        assert result['cta_effectiveness'] == 'insufficient_data'
class TestStoriesPerformance:
    def test_stories_analysis(self, sample_stories):
        analyzer = InstagramContentAnalyzer(media=[], stories=sample_stories)
        result = analyzer.analyze_stories_performance()
        assert result['success'] is True
        assert 'stories_analyzed' in result
        assert 'total_reach' in result
        assert 'total_impressions' in result
        assert 'total_replies' in result
        assert 'avg_completion_rate' in result
        assert 'reply_rate' in result
    def test_stories_metrics_calculation(self, sample_stories):
        analyzer = InstagramContentAnalyzer(media=[], stories=sample_stories)
        result = analyzer.analyze_stories_performance()
        assert result['stories_analyzed'] == 2
        assert result['total_reach'] == 2500
        assert result['total_replies'] == 35
    def test_no_stories_data(self):
        analyzer = InstagramContentAnalyzer(media=[])
        result = analyzer.analyze_stories_performance()
        assert result['success'] is False
        assert result['stories_analyzed'] == 0
class TestFashionInsights:
    def test_fashion_insights_generation(self, sample_media):
        analyzer = InstagramContentAnalyzer(media=sample_media)
        insights = analyzer._get_fashion_insights()
        assert insights['success'] is True
        assert 'avg_save_rate' in insights
        assert 'save_rate_benchmark' in insights
        assert 'benchmark_description' in insights
        assert 'best_performing_product' in insights
        assert 'recommendation' in insights
    def test_save_rate_benchmarks(self):
        media_excellent = [
            {
                "media_id": "1",
                "saved": 400,
                "reach": 10000
            }
        ]
        analyzer = InstagramContentAnalyzer(media=media_excellent)
        insights = analyzer._get_fashion_insights()
        assert insights['save_rate_benchmark'] == 'excellent'
        assert insights['avg_save_rate'] > 3.0
        media_good = [
            {
                "media_id": "1",
                "saved": 200,
                "reach": 10000
            }
        ]
        analyzer = InstagramContentAnalyzer(media=media_good)
        insights = analyzer._get_fashion_insights()
        assert insights['save_rate_benchmark'] == 'good'
        assert 1.0 < insights['avg_save_rate'] <= 3.0
        media_poor = [
            {
                "media_id": "1",
                "saved": 50,
                "reach": 10000
            }
        ]
        analyzer = InstagramContentAnalyzer(media=media_poor)
        insights = analyzer._get_fashion_insights()
        assert insights['save_rate_benchmark'] == 'poor'
        assert insights['avg_save_rate'] < 1.0
    def test_best_product_category_detection(self, sample_media):
        analyzer = InstagramContentAnalyzer(media=sample_media)
        best_product = analyzer._find_best_product_category()
        assert isinstance(best_product, str)
    def test_no_data_insights(self):
        analyzer = InstagramContentAnalyzer(media=[])
        insights = analyzer._get_fashion_insights()
        assert insights['success'] is False
        assert insights['avg_save_rate'] == 0
class TestFullAnalysis:
    def test_full_analysis_structure(self, sample_media, sample_stories):
        analyzer = InstagramContentAnalyzer(
            media=sample_media,
            stories=sample_stories
        )
        analysis = analyzer.get_full_analysis()
        assert 'posts_analyzed' in analysis
        assert 'top_posts_by_saves' in analysis
        assert 'content_types' in analysis
        assert 'hashtags' in analysis
        assert 'posting_patterns' in analysis
        assert 'captions' in analysis
        assert 'stories' in analysis
        assert 'insights_for_fashion_brand' in analysis
    def test_full_analysis_components(self, sample_media):
        analyzer = InstagramContentAnalyzer(media=sample_media)
        analysis = analyzer.get_full_analysis()
        assert analysis['posts_analyzed'] == len(sample_media)
        assert len(analysis['top_posts_by_saves']) > 0
        assert analysis['content_types']['success'] is True
        assert len(analysis['hashtags']) > 0
        assert analysis['posting_patterns']['success'] is True
        assert analysis['captions']['success'] is True
        assert analysis['insights_for_fashion_brand']['success'] is True
class TestHelperMethods:
    def test_safe_numeric_conversion(self):
        analyzer = InstagramContentAnalyzer(media=[])
        assert analyzer._safe_numeric(100) == 100.0
        assert analyzer._safe_numeric("50") == 50.0
        assert analyzer._safe_numeric(None, default=10) == 10.0
        assert analyzer._safe_numeric("invalid", default=5) == 5.0
    def test_extract_hashtags_edge_cases(self):
        analyzer = InstagramContentAnalyzer(media=[])
        assert analyzer._extract_hashtags("") == []
        assert analyzer._extract_hashtags(None) == []
        hashtags = analyzer._extract_hashtags("#one #two #three")
        assert len(hashtags) == 3
        hashtags = analyzer._extract_hashtags("#Fashion #STYLE")
        assert "fashion" in hashtags
        assert "style" in hashtags
    def test_parse_timestamp_invalid(self):
        analyzer = InstagramContentAnalyzer(media=[])
        assert analyzer._parse_timestamp("invalid") is None
        assert analyzer._parse_timestamp("") is None
        assert analyzer._parse_timestamp(None) is None
class TestEdgeCases:
    def test_empty_media_list(self):
        analyzer = InstagramContentAnalyzer(media=[])
        assert analyzer.get_top_performing() == []
        assert analyzer.analyze_hashtags() == []
        content_types = analyzer.analyze_content_types()
        assert content_types['success'] is False
        patterns = analyzer.analyze_posting_patterns()
        assert patterns['success'] is False
        captions = analyzer.analyze_captions()
        assert captions['success'] is False
    def test_media_with_missing_fields(self):
        incomplete_media = [
            {
                "media_id": "1",
                "media_type": "IMAGE"
            },
            {
                "media_id": "2",
                "media_type": "VIDEO",
                "saved": 100,
                "reach": 1000
            }
        ]
        analyzer = InstagramContentAnalyzer(media=incomplete_media)
        top = analyzer.get_top_performing(metric="saves")
        assert len(top) == 2
    def test_media_with_none_values(self):
        media_with_nones = [
            {
                "media_id": "1",
                "saved": None,
                "reach": None,
                "likes": None
            }
        ]
        analyzer = InstagramContentAnalyzer(media=media_with_nones)
        top = analyzer.get_top_performing(metric="saves")
        assert len(top) == 1
        assert analyzer._safe_numeric(top[0].get("saved")) == 0.0
    def test_analyzer_initialization_logging(self, sample_media, caplog):
        import logging
        caplog.set_level(logging.INFO)
        analyzer = InstagramContentAnalyzer(media=sample_media)
        assert "Initialized analyzer" in caplog.text
