import streamlit as st
import pandas as pd
from typing import List, Dict, Optional
from datetime import datetime
from dashboard.config import CACHE_TTL, LOGS_CACHE_TTL
@st.cache_data(ttl=CACHE_TTL)
def fetch_accounts_cached(platform: Optional[str] = None, is_active: bool = True) -> List[Dict]:
    from dashboard.services.api_client import get_api_client
    client = get_api_client()
    return client.get_accounts(platform=platform, is_active=is_active)
@st.cache_data(ttl=CACHE_TTL)
def fetch_metrics_cached(
    platform: Optional[str],
    start_date: datetime,
    end_date: datetime,
    account_id: Optional[str] = None
) -> pd.DataFrame:
    from dashboard.services.api_client import get_api_client
    from dashboard.services.data_processor import MetricsProcessor
    client = get_api_client()
    metrics = client.get_metrics(
        platform=platform,
        start_date=start_date,
        end_date=end_date,
        account_id=account_id
    )
    processor = MetricsProcessor()
    return processor.to_dataframe(metrics)
@st.cache_data(ttl=LOGS_CACHE_TTL)
def fetch_collection_logs_cached(limit: int = 10) -> pd.DataFrame:
    from dashboard.services.api_client import get_api_client
    from dashboard.services.data_processor import MetricsProcessor
    client = get_api_client()
    logs = client.get_collection_logs(limit=limit)
    processor = MetricsProcessor()
    return processor.logs_to_dataframe(logs)
def clear_all_caches():
    st.cache_data.clear()
    st.cache_resource.clear()
