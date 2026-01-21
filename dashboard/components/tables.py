import streamlit as st
import pandas as pd
from dashboard.utils.formatters import format_compact, format_percent, format_datetime, format_duration
from dashboard.utils.constants import STATUS_COLORS
def render_metrics_table(df: pd.DataFrame):
    if df.empty:
        st.info("Нет данных для отображения")
        return
    display_df = pd.DataFrame({
        'Аккаунт': df.get('display_name', df.get('account_id', '')),
        'Подписчики': df['followers'].apply(lambda x: format_compact(x) if pd.notna(x) else '—'),
        'Вовлеченность': df['engagement_rate'].apply(lambda x: format_percent(x) if pd.notna(x) else '—'),
        'Публикации': df['posts_count'].apply(lambda x: format_compact(x) if pd.notna(x) else '—'),
        'Обновлено': df['collected_at'].apply(format_datetime)
    })
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True
    )
def render_logs_table(df: pd.DataFrame):
    if df.empty:
        st.info("Нет логов сбора")
        return
    display_df = pd.DataFrame({
        'Время запуска': df['started_at'].apply(format_datetime),
        'Статус': df['status'],
        'Обработано': df['accounts_processed'],
        'Ошибки': df['accounts_failed'],
        'Длительность': df.get('duration', pd.Series([None] * len(df))).apply(format_duration)
    })
    def color_status(val):
        color = STATUS_COLORS.get(val, '#000000')
        return f'background-color: {color}; color: white'
    styled_df = display_df.style.applymap(
        color_status,
        subset=['Статус']
    )
    st.dataframe(
        styled_df,
        use_container_width=True,
        hide_index=True
    )
