import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from dashboard.config import PAGE_TITLE, PAGE_ICON
from dashboard.utils.session_state import init_session_state
from dashboard.utils.constants import PLATFORM_COLORS
from dashboard.components.filters import render_date_range_filter, render_account_filter
from dashboard.components.kpi_cards import render_kpi_card
from dashboard.components.charts import ChartBuilder
from dashboard.components.tables import render_metrics_table
from dashboard.components.account_manager import render_account_card
from dashboard.services.cache_manager import (
    fetch_accounts_cached,
    fetch_metrics_cached,
    clear_all_caches
)
from dashboard.services.data_processor import MetricsProcessor
from dashboard.services.api_client import get_api_client
st.set_page_config(
    page_title=f"Дзен - {PAGE_TITLE}",
    page_icon="📝",
    layout="wide"
)
init_session_state()
st.title("📝 Яндекс Дзен Analytics")
st.markdown("Аналитика каналов Яндекс Дзен")
st.markdown("---")
col1, col2 = st.columns([2, 3])
with col1:
    try:
        dzen_accounts = fetch_accounts_cached(platform='dzen')
    except Exception as e:
        st.error(f"⚠️ Ошибка загрузки аккаунтов: {e}")
        st.stop()
    if not dzen_accounts:
        st.warning("⚠️ Нет аккаунтов Яндекс Дзен")
        st.markdown("""
        **Действия:**
        - Добавьте Дзен аккаунты через API
        - Запустите сбор данных
        **Пример добавления через API:**
        ```bash
        curl -X POST http://localhost:8000/api/v1/accounts \\
          -H "Content-Type: application/json" \\
          -d '{
            "platform": "dzen",
            "account_id": "68d24f523b89f667f57816e2",
            "account_url": "https://dzen.ru/id/68d24f523b89f667f57816e2",
            "display_name": "NIGINart Дзен"
          }'
        ```
        """)
        st.stop()
    selected_account_id = render_account_filter(dzen_accounts)
with col2:
    start_date, end_date = render_date_range_filter()
try:
    with st.spinner("Загрузка метрик..."):
        metrics_df = fetch_metrics_cached(
            platform='dzen',
            start_date=start_date,
            end_date=end_date,
            account_id=None if selected_account_id == 'all' else selected_account_id
        )
except Exception as e:
    st.error(f"⚠️ Ошибка загрузки метрик: {e}")
    st.stop()
if metrics_df.empty:
    st.info("📊 Нет данных за выбранный период")
    st.markdown("""
    **Возможные причины:**
    - Сбор данных еще не запускался
    - Нет данных за указанный период
    - Парсинг Дзен может быть заблокирован (требуется прокси)
    **Действия:**
    - Запустить сбор данных: `POST /api/v1/collect?platform=dzen`
    - Настроить прокси в `.env` (PROXY_URL)
    - Расширить временной диапазон
    """)
    st.stop()
processor = MetricsProcessor()
latest_df = processor.aggregate_by_account(metrics_df)
current_followers = int(latest_df['followers'].sum()) if 'followers' in latest_df.columns else 0
current_views = int(latest_df['total_views'].sum()) if 'total_views' in latest_df.columns else 0
current_likes = int(latest_df['total_likes'].sum()) if 'total_likes' in latest_df.columns else 0
current_posts = int(latest_df['posts_count'].sum()) if 'posts_count' in latest_df.columns else 0
current_engagement = float(latest_df['engagement_rate'].mean()) if 'engagement_rate' in latest_df.columns else 0
period_length = (end_date - start_date).days
if period_length > 0:
    prev_start = start_date - timedelta(days=period_length)
    prev_end = start_date
    try:
        prev_metrics_df = fetch_metrics_cached(
            platform='dzen',
            start_date=prev_start,
            end_date=prev_end,
            account_id=None if selected_account_id == 'all' else selected_account_id
        )
        if not prev_metrics_df.empty:
            prev_latest = processor.aggregate_by_account(prev_metrics_df)
            prev_followers = int(prev_latest['followers'].sum()) if 'followers' in prev_latest.columns else 0
            prev_views = int(prev_latest['total_views'].sum()) if 'total_views' in prev_latest.columns else 0
            prev_likes = int(prev_latest['total_likes'].sum()) if 'total_likes' in prev_latest.columns else 0
            prev_posts = int(prev_latest['posts_count'].sum()) if 'posts_count' in prev_latest.columns else 0
            delta_followers = current_followers - prev_followers
            delta_views = current_views - prev_views
            delta_likes = current_likes - prev_likes
            delta_posts = current_posts - prev_posts
        else:
            delta_followers = delta_views = delta_likes = delta_posts = None
    except:
        delta_followers = delta_views = delta_likes = delta_posts = None
else:
    delta_followers = delta_views = delta_likes = delta_posts = None
st.markdown("---")
st.subheader("Ключевые показатели")
col1, col2, col3, col4 = st.columns(4)
with col1:
    render_kpi_card(
        "Подписчики",
        current_followers,
        delta=delta_followers,
        format_type='compact'
    )
with col2:
    render_kpi_card(
        "Просмотры",
        current_views,
        delta=delta_views,
        format_type='compact'
    )
with col3:
    render_kpi_card(
        "Лайки",
        current_likes,
        delta=delta_likes,
        format_type='compact'
    )
with col4:
    render_kpi_card(
        "Публикации",
        current_posts,
        delta=delta_posts,
        format_type='number'
    )
st.markdown("---")
tab1, tab2, tab3 = st.tabs(["📈 Динамика", "📊 Сравнение", "⚙️ Аккаунты"])
with tab1:
    st.subheader("Динамика показателей")
    if len(metrics_df) > 1 and 'followers' in metrics_df.columns:
        followers_ts = processor.prepare_time_series(metrics_df, 'followers', resample_freq='D')
        if not followers_ts.empty and len(followers_ts) > 1:
            chart = ChartBuilder.line_chart(
                followers_ts,
                x='collected_at',
                y='followers',
                title='Динамика подписчиков',
                y_label='Подписчики',
                color=PLATFORM_COLORS['dzen']
            )
            st.plotly_chart(chart, use_container_width=True)
    if len(metrics_df) > 1 and 'total_views' in metrics_df.columns:
        views_ts = processor.prepare_time_series(metrics_df, 'total_views', resample_freq='D')
        if not views_ts.empty and len(views_ts) > 1:
            chart = ChartBuilder.line_chart(
                views_ts,
                x='collected_at',
                y='total_views',
                title='Динамика просмотров',
                y_label='Просмотры',
                color=PLATFORM_COLORS['dzen']
            )
            st.plotly_chart(chart, use_container_width=True)
    if len(metrics_df) > 1 and 'total_likes' in metrics_df.columns:
        likes_ts = processor.prepare_time_series(metrics_df, 'total_likes', resample_freq='D')
        if not likes_ts.empty and len(likes_ts) > 1:
            chart = ChartBuilder.line_chart(
                likes_ts,
                x='collected_at',
                y='total_likes',
                title='Динамика лайков',
                y_label='Лайки',
                color=PLATFORM_COLORS['dzen']
            )
            st.plotly_chart(chart, use_container_width=True)
    if len(metrics_df) > 1 and 'engagement_rate' in metrics_df.columns:
        er_ts = processor.prepare_time_series(metrics_df, 'engagement_rate', resample_freq='D')
        if not er_ts.empty and len(er_ts) > 1:
            chart = ChartBuilder.line_chart(
                er_ts,
                x='collected_at',
                y='engagement_rate',
                title='Динамика вовлеченности',
                y_label='ER %',
                color=PLATFORM_COLORS['dzen']
            )
            st.plotly_chart(chart, use_container_width=True)
with tab2:
    st.subheader("Сравнение аккаунтов")
    if selected_account_id == 'all' and len(latest_df) > 1:
        latest_sorted = latest_df.sort_values('followers', ascending=True)
        chart = ChartBuilder.bar_chart(
            latest_sorted,
            x='followers',
            y='display_name' if 'display_name' in latest_sorted.columns else 'account_id',
            title='Подписчики по аккаунтам',
            x_label='Подписчики',
            y_label='Аккаунт',
            color=PLATFORM_COLORS['dzen']
        )
        st.plotly_chart(chart, use_container_width=True)
        if 'total_views' in latest_df.columns:
            views_sorted = latest_df.sort_values('total_views', ascending=True)
            chart = ChartBuilder.bar_chart(
                views_sorted,
                x='total_views',
                y='display_name' if 'display_name' in views_sorted.columns else 'account_id',
                title='Просмотры по аккаунтам',
                x_label='Просмотры',
                y_label='Аккаунт',
                color=PLATFORM_COLORS['dzen']
            )
            st.plotly_chart(chart, use_container_width=True)
        if 'total_likes' in latest_df.columns:
            likes_sorted = latest_df.sort_values('total_likes', ascending=True)
            chart = ChartBuilder.bar_chart(
                likes_sorted,
                x='total_likes',
                y='display_name' if 'display_name' in likes_sorted.columns else 'account_id',
                title='Лайки по аккаунтам',
                x_label='Лайки',
                y_label='Аккаунт',
                color=PLATFORM_COLORS['dzen']
            )
            st.plotly_chart(chart, use_container_width=True)
    else:
        st.info("Выберите 'Все аккаунты' для сравнения")
    st.markdown("---")
    st.subheader("Последние метрики")
    render_metrics_table(latest_df)
with tab3:
    st.subheader("Управление аккаунтами")
    def toggle_account_status(account_id: str, new_status: bool):
        try:
            client = get_api_client()
            client.update_account_status(account_id, new_status)
            clear_all_caches()
            st.success(f"✅ Статус аккаунта обновлен")
        except Exception as e:
            st.error(f"⚠️ Ошибка обновления: {e}")
    if dzen_accounts:
        for account in dzen_accounts:
            render_account_card(account, on_toggle=toggle_account_status)
    else:
        st.info("Нет аккаунтов для отображения")
    st.markdown("---")
    st.info("""
    **Примечание о парсинге Яндекс Дзен:**
    - Дзен не имеет публичного API, данные собираются через парсинг HTML
    - Для стабильной работы рекомендуется настроить прокси
    - Парсинг может занять больше времени из-за JavaScript-рендеринга
    """)
st.markdown("---")
st.caption(f"Последнее обновление: {datetime.now().strftime('%d.%m.%Y %H:%M')}")
