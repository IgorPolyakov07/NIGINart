import streamlit as st
import pandas as pd
from datetime import datetime
from dashboard.config import PAGE_TITLE, PAGE_ICON, LAYOUT
from dashboard.utils.session_state import init_session_state
from dashboard.utils.constants import PLATFORM_COLORS, PLATFORM_NAMES
from dashboard.components.filters import render_date_range_filter
from dashboard.components.kpi_cards import render_kpi_card
from dashboard.components.charts import ChartBuilder
from dashboard.components.tables import render_logs_table
from dashboard.services.cache_manager import (
    fetch_accounts_cached,
    fetch_metrics_cached,
    fetch_collection_logs_cached
)
from dashboard.services.data_processor import MetricsProcessor
st.set_page_config(
    page_title=PAGE_TITLE,
    page_icon=PAGE_ICON,
    layout=LAYOUT
)
init_session_state()
st.title(f"{PAGE_ICON} NIGINart Analytics Dashboard")
st.markdown("Общий обзор всех платформ")
st.markdown("---")
start_date, end_date = render_date_range_filter()
try:
    with st.spinner("Загрузка данных..."):
        all_accounts = fetch_accounts_cached()
        logs_df = fetch_collection_logs_cached(limit=5)
        platform_data = {}
        for platform in ['telegram', 'youtube', 'vk', 'tiktok']:
            metrics_df = fetch_metrics_cached(
                platform=platform,
                start_date=start_date,
                end_date=end_date
            )
            if not metrics_df.empty:
                platform_data[platform] = metrics_df
except Exception as e:
    st.error(f"⚠️ Ошибка подключения к API: {e}")
    st.markdown("""
    **Проверьте:**
    - Запущен ли FastAPI? http://localhost:8000/health
    - Доступна ли база данных?
    """)
    st.stop()
st.markdown("---")
st.subheader("Ключевые показатели")
col1, col2, col3, col4 = st.columns(4)
total_accounts = len(all_accounts)
active_accounts = len([a for a in all_accounts if a.get('is_active')])
total_followers = 0
total_engagement = 0
platform_count = 0
for platform, df in platform_data.items():
    summary = MetricsProcessor.calculate_platform_summary(df)
    total_followers += summary['total_followers']
    if summary['avg_engagement_rate'] > 0:
        total_engagement += summary['avg_engagement_rate']
        platform_count += 1
avg_engagement = total_engagement / platform_count if platform_count > 0 else 0
with col1:
    render_kpi_card("Всего аккаунтов", total_accounts, format_type='number')
with col2:
    render_kpi_card("Активные аккаунты", active_accounts, format_type='number')
with col3:
    render_kpi_card("Средняя вовлеченность", avg_engagement, format_type='percent')
with col4:
    render_kpi_card("Всего подписчиков", total_followers, format_type='compact')
st.markdown("---")
st.subheader("Обзор по платформам")
platform_cols = st.columns(4)
for idx, platform in enumerate(['telegram', 'youtube', 'vk', 'tiktok']):
    with platform_cols[idx]:
        st.markdown(f"### {PLATFORM_NAMES[platform]}")
        if platform in platform_data:
            df = platform_data[platform]
            summary = MetricsProcessor.calculate_platform_summary(df)
            st.metric("Подписчики", f"{summary['total_followers']:,}")
            st.metric("Вовлеченность", f"{summary['avg_engagement_rate']:.1f}%")
            st.metric("Аккаунты", summary['total_accounts'])
            if len(df) > 1:
                processor = MetricsProcessor()
                ts_df = processor.prepare_time_series(df, 'engagement_rate', resample_freq='D')
                if not ts_df.empty and len(ts_df) > 1:
                    chart = ChartBuilder.line_chart(
                        ts_df,
                        x='collected_at',
                        y='engagement_rate',
                        title='',
                        y_label='ER %',
                        color=PLATFORM_COLORS[platform]
                    )
                    chart.update_layout(height=200, margin=dict(l=20, r=20, t=20, b=20))
                    st.plotly_chart(chart, use_container_width=True)
        else:
            st.info("Нет данных")
if platform_data:
    st.markdown("---")
    st.subheader("Динамика вовлеченности")
    all_dfs = []
    for platform, df in platform_data.items():
        df_copy = df.copy()
        df_copy['platform'] = platform
        all_dfs.append(df_copy)
    if all_dfs:
        combined_df = pd.concat(all_dfs, ignore_index=True)
        processor = MetricsProcessor()
        platform_series = {}
        for platform in ['telegram', 'youtube', 'vk', 'tiktok']:
            platform_df = combined_df[combined_df['platform'] == platform]
            if not platform_df.empty and len(platform_df) > 1:
                ts = processor.prepare_time_series(platform_df, 'engagement_rate', resample_freq='D')
                if not ts.empty:
                    platform_series[platform] = ts
        if platform_series:
            merged = None
            for platform, ts in platform_series.items():
                ts_renamed = ts.rename(columns={'engagement_rate': platform})
                if merged is None:
                    merged = ts_renamed
                else:
                    merged = merged.merge(ts_renamed, on='collected_at', how='outer')
            if merged is not None and len(merged) > 1:
                merged = merged.fillna(method='ffill').fillna(0)
                chart = ChartBuilder.multi_line_chart(
                    merged,
                    x='collected_at',
                    y_columns=[p for p in ['telegram', 'youtube', 'vk', 'tiktok'] if p in merged.columns],
                    title='Вовлеченность по платформам',
                    y_label='ER %',
                    legend_labels=[PLATFORM_NAMES[p] for p in ['telegram', 'youtube', 'vk', 'tiktok'] if p in merged.columns]
                )
                st.plotly_chart(chart, use_container_width=True)
st.markdown("---")
st.subheader("Последние сборы данных")
if not logs_df.empty:
    render_logs_table(logs_df)
else:
    st.info("Нет данных о сборах")
st.markdown("---")
st.caption(f"Последнее обновление: {datetime.now().strftime('%d.%m.%Y %H:%M')}")
