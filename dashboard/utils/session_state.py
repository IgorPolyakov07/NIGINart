import streamlit as st
from datetime import datetime, timedelta
from typing import Tuple
from dashboard.utils.constants import DATE_RANGE_PRESETS
def init_session_state():
    if 'date_range' not in st.session_state:
        st.session_state.date_range = 'all_time'
    if 'custom_start_date' not in st.session_state:
        st.session_state.custom_start_date = datetime(2020, 1, 1)
    if 'custom_end_date' not in st.session_state:
        st.session_state.custom_end_date = datetime.now()
    if 'selected_account' not in st.session_state:
        st.session_state.selected_account = 'all'
    if 'last_refresh' not in st.session_state:
        st.session_state.last_refresh = datetime.now()
def get_date_range() -> Tuple[datetime, datetime]:
    if st.session_state.date_range == 'custom':
        return (
            st.session_state.custom_start_date,
            st.session_state.custom_end_date
        )
    elif st.session_state.date_range == 'all_time':
        start_date = datetime(2020, 1, 1)
        end_date = datetime.now()
        return start_date, end_date
    else:
        days = DATE_RANGE_PRESETS.get(st.session_state.date_range, 30)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        return start_date, end_date
def update_date_range(preset: str):
    st.session_state.date_range = preset
    from dashboard.services.cache_manager import clear_all_caches
    clear_all_caches()
def refresh_data():
    st.session_state.last_refresh = datetime.now()
    from dashboard.services.cache_manager import clear_all_caches
    clear_all_caches()
