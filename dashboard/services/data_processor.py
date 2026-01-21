import pandas as pd
from typing import List, Dict, Optional
from datetime import datetime
class MetricsProcessor:
    @staticmethod
    def to_dataframe(metrics: List[Dict]) -> pd.DataFrame:
        if not metrics:
            return pd.DataFrame()
        df = pd.DataFrame(metrics)
        df['collected_at'] = pd.to_datetime(df['collected_at'])
        df = df.sort_values('collected_at')
        if 'extra_data' in df.columns and df['extra_data'].notna().any():
            extra_df = pd.json_normalize(df['extra_data'])
            df = pd.concat([df.drop('extra_data', axis=1), extra_df], axis=1)
        return df
    @staticmethod
    def calculate_growth(df: pd.DataFrame, metric: str) -> pd.DataFrame:
        if df.empty or metric not in df.columns:
            return df
        df = df.sort_values('collected_at')
        df[f'{metric}_prev'] = df.groupby('account_id')[metric].shift(1)
        df[f'{metric}_change'] = df[metric] - df[f'{metric}_prev']
        df[f'{metric}_pct_change'] = (
            (df[metric] - df[f'{metric}_prev']) / df[f'{metric}_prev'].replace(0, 1) * 100
        )
        return df
    @staticmethod
    def aggregate_by_account(df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df
        latest = df.sort_values('collected_at').groupby('account_id').tail(1)
        return latest.reset_index(drop=True)
    @staticmethod
    def calculate_platform_summary(df: pd.DataFrame) -> Dict:
        if df.empty:
            return {
                'total_followers': 0,
                'total_accounts': 0,
                'avg_engagement_rate': 0.0,
                'total_posts': 0,
                'last_updated': None
            }
        latest = MetricsProcessor.aggregate_by_account(df)
        return {
            'total_followers': int(latest['followers'].sum()) if 'followers' in latest else 0,
            'total_accounts': len(latest),
            'avg_engagement_rate': float(latest['engagement_rate'].mean()) if 'engagement_rate' in latest else 0.0,
            'total_posts': int(latest['posts_count'].sum()) if 'posts_count' in latest else 0,
            'last_updated': latest['collected_at'].max() if 'collected_at' in latest else None
        }
    @staticmethod
    def prepare_time_series(
        df: pd.DataFrame,
        metric: str,
        resample_freq: Optional[str] = None
    ) -> pd.DataFrame:
        if df.empty or metric not in df.columns:
            return pd.DataFrame()
        df_copy = df.copy()
        df_copy = df_copy.set_index('collected_at')
        data_points = len(df_copy[metric].dropna())
        if resample_freq is None:
            if data_points <= 5:
                result = df_copy[[metric]].dropna()
                return result.reset_index()
            elif data_points <= 20:
                freq = 'W'
            else:
                freq = 'D'
        else:
            freq = resample_freq
        resampled = df_copy[metric].resample(freq).mean()
        resampled = resampled.dropna()
        return resampled.reset_index()
    @staticmethod
    def logs_to_dataframe(logs: List[Dict]) -> pd.DataFrame:
        if not logs:
            return pd.DataFrame()
        df = pd.DataFrame(logs)
        df['started_at'] = pd.to_datetime(df['started_at'])
        if 'finished_at' in df.columns:
            df['finished_at'] = pd.to_datetime(df['finished_at'])
            df['duration'] = (df['finished_at'] - df['started_at']).dt.total_seconds()
        return df.sort_values('started_at', ascending=False)
    @staticmethod
    def accounts_to_dataframe(accounts: List[Dict]) -> pd.DataFrame:
        if not accounts:
            return pd.DataFrame()
        df = pd.DataFrame(accounts)
        if 'created_at' in df.columns:
            df['created_at'] = pd.to_datetime(df['created_at'])
        if 'updated_at' in df.columns:
            df['updated_at'] = pd.to_datetime(df['updated_at'])
        return df.sort_values(['platform', 'display_name'])
