import streamlit as st
from datetime import datetime, timedelta
from typing import Tuple, List, Dict
from dashboard.utils.constants import DATE_RANGE_LABELS
from dashboard.utils.session_state import get_date_range
def render_date_range_filter() -> Tuple[datetime, datetime]:
    col1, col2 = st.columns([3, 1])
    with col1:
        PRESET_ORDER = [
            'all_time',
            'last_7_days',
            'last_30_days',
            'last_90_days',
            'last_6_months',
            'last_year',
            'custom'
        ]
        preset = st.selectbox(
            "Период",
            options=PRESET_ORDER,
            format_func=lambda x: DATE_RANGE_LABELS[x],
            key='date_range'
        )
    with col2:
        if st.button("🔄 Обновить", use_container_width=True):
            from dashboard.utils.session_state import refresh_data
            refresh_data()
            st.rerun()
    if preset == 'custom':
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input(
                "С",
                value=st.session_state.custom_start_date,
                key='custom_start_date'
            )
        with col2:
            end_date = st.date_input(
                "До",
                value=st.session_state.custom_end_date,
                key='custom_end_date'
            )
        return datetime.combine(start_date, datetime.min.time()), datetime.combine(end_date, datetime.max.time())
    return get_date_range()
def render_account_filter(accounts: List[Dict]) -> str:
    if not accounts:
        st.info("Нет доступных аккаунтов")
        return 'all'
    options = [{'id': 'all', 'name': 'Все аккаунты'}] + [
        {'id': acc['id'], 'name': acc['display_name']}
        for acc in accounts
    ]
    selected = st.selectbox(
        "Аккаунт",
        options=range(len(options)),
        format_func=lambda i: options[i]['name'],
        key='selected_account_idx'
    )
    return options[selected]['id']
