import pandas as pd
import pytest
from datetime import datetime, timedelta
from dashboard.services.data_processor import MetricsProcessor
class TestAdaptiveResampling:
    def test_adaptive_resampling_single_point(self):
        df = pd.DataFrame({
            'collected_at': [datetime(2025, 12, 21, 10, 0)],
            'followers': [1000]
        })
        result = MetricsProcessor.prepare_time_series(df, 'followers')
        assert len(result) == 1
        assert result['followers'].iloc[0] == 1000
        assert 'collected_at' in result.columns
    def test_adaptive_resampling_sparse_5points(self):
        base_date = datetime(2025, 12, 15)
        dates = [base_date + timedelta(days=i) for i in range(5)]
        df = pd.DataFrame({
            'collected_at': dates,
            'followers': [1000, 1050, 1100, 1150, 1200]
        })
        result = MetricsProcessor.prepare_time_series(df, 'followers')
        assert len(result) == 5
        assert result['followers'].tolist() == [1000, 1050, 1100, 1150, 1200]
    def test_adaptive_resampling_medium_10points(self):
        base_date = datetime(2025, 10, 1)
        dates = [base_date + timedelta(days=i*3) for i in range(10)]
        df = pd.DataFrame({
            'collected_at': dates,
            'followers': [1000 + i*100 for i in range(10)]
        })
        result = MetricsProcessor.prepare_time_series(df, 'followers')
        assert len(result) <= 10
        assert len(result) > 0
        assert 'collected_at' in result.columns
        assert 'followers' in result.columns
    def test_adaptive_resampling_dense_50points(self):
        base_date = datetime(2025, 1, 1)
        dates = [base_date + timedelta(hours=i*12) for i in range(50)]
        df = pd.DataFrame({
            'collected_at': dates,
            'followers': [1000 + i*10 for i in range(50)]
        })
        result = MetricsProcessor.prepare_time_series(df, 'followers')
        assert len(result) <= 50
        assert len(result) > 0
        assert 'collected_at' in result.columns
    def test_nan_filtering(self):
        df = pd.DataFrame({
            'collected_at': [datetime(2025, 12, i) for i in range(1, 6)],
            'followers': [1000, None, 1200, None, 1400]
        })
        result = MetricsProcessor.prepare_time_series(df, 'followers')
        assert len(result) == 3
        assert result['followers'].notna().all()
        assert result['followers'].tolist() == [1000, 1200, 1400]
    def test_manual_frequency_override(self):
        base_date = datetime(2025, 1, 1)
        dates = [base_date + timedelta(days=i) for i in range(20)]
        df = pd.DataFrame({
            'collected_at': dates,
            'followers': [1000 + i*10 for i in range(20)]
        })
        result = MetricsProcessor.prepare_time_series(df, 'followers', resample_freq='D')
        assert len(result) <= 20
        assert 'collected_at' in result.columns
    def test_empty_dataframe(self):
        df = pd.DataFrame()
        result = MetricsProcessor.prepare_time_series(df, 'followers')
        assert result.empty
    def test_missing_metric_column(self):
        df = pd.DataFrame({
            'collected_at': [datetime(2025, 12, 21)],
            'other_metric': [100]
        })
        result = MetricsProcessor.prepare_time_series(df, 'followers')
        assert result.empty
