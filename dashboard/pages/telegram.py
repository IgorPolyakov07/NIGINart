import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from collections import Counter
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
    page_title=f"Telegram - {PAGE_TITLE}",
    page_icon="📱",
    layout="wide"
)
init_session_state()
st.title("📱 Telegram Analytics")
st.markdown("Аналитика каналов Telegram")
st.markdown("---")
col1, col2 = st.columns([2, 3])
with col1:
    try:
        telegram_accounts = fetch_accounts_cached(platform='telegram')
    except Exception as e:
        st.error(f"⚠️ Ошибка загрузки аккаунтов: {e}")
        st.stop()
    if not telegram_accounts:
        st.warning("⚠️ Нет аккаунтов Telegram")
        st.markdown("""
        **Действия:**
        - Добавьте Telegram аккаунты через API
        - Запустите сбор данных
        """)
        st.stop()
    selected_account_id = render_account_filter(telegram_accounts)
with col2:
    start_date, end_date = render_date_range_filter()
try:
    with st.spinner("Загрузка метрик..."):
        metrics_df = fetch_metrics_cached(
            platform='telegram',
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
    **Действия:**
    - Запустить сбор данных
    - Расширить временной диапазон
    """)
    st.stop()
processor = MetricsProcessor()
latest_df = processor.aggregate_by_account(metrics_df)
current_followers = int(latest_df['followers'].sum())
current_posts = int(latest_df['posts_count'].sum())
current_engagement = float(latest_df['engagement_rate'].mean())
current_avg_views = 0
if 'avg_views' in latest_df.columns:
    current_avg_views = float(latest_df['avg_views'].mean())
period_length = (end_date - start_date).days
if period_length > 0:
    prev_start = start_date - timedelta(days=period_length)
    prev_end = start_date
    try:
        prev_metrics_df = fetch_metrics_cached(
            platform='telegram',
            start_date=prev_start,
            end_date=prev_end,
            account_id=None if selected_account_id == 'all' else selected_account_id
        )
        if not prev_metrics_df.empty:
            prev_latest = processor.aggregate_by_account(prev_metrics_df)
            prev_followers = int(prev_latest['followers'].sum())
            prev_posts = int(prev_latest['posts_count'].sum())
            prev_engagement = float(prev_latest['engagement_rate'].mean())
            prev_avg_views = float(prev_latest['avg_views'].mean()) if 'avg_views' in prev_latest.columns else 0
            delta_followers = current_followers - prev_followers
            delta_posts = current_posts - prev_posts
            delta_engagement = current_engagement - prev_engagement
            delta_avg_views = current_avg_views - prev_avg_views
        else:
            delta_followers = delta_posts = delta_engagement = delta_avg_views = None
    except:
        delta_followers = delta_posts = delta_engagement = delta_avg_views = None
else:
    delta_followers = delta_posts = delta_engagement = delta_avg_views = None
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
        "Средние просмотры",
        current_avg_views,
        delta=delta_avg_views,
        format_type='compact'
    )
with col3:
    render_kpi_card(
        "Публикации",
        current_posts,
        delta=delta_posts,
        format_type='number'
    )
with col4:
    render_kpi_card(
        "Вовлеченность",
        current_engagement,
        delta=delta_engagement,
        format_type='percent'
    )
if not latest_df.empty and 'extra_data' in latest_df.columns:
    extra_data = latest_df.iloc[0]['extra_data'] if latest_df.iloc[0]['extra_data'] else {}
    if extra_data:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            avg_reactions = extra_data.get('avg_reactions', 0)
            st.metric("Средние реакции", f"{avg_reactions:.1f}")
        with col2:
            avg_forwards = extra_data.get('avg_forwards', 0)
            st.metric("Средние репосты", f"{avg_forwards:.1f}")
        with col3:
            sample_size = extra_data.get('sample_size', 0)
            st.metric("Проанализировано постов", sample_size)
        with col4:
            auth_mode = extra_data.get('auth_mode', 'unknown')
            st.metric("Режим авторизации", auth_mode.upper())
st.markdown("---")
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📈 Динамика", "📊 Сравнение", "🔥 Топ посты", "🎭 Реакции", "⚙️ Аккаунты"])
with tab1:
    st.subheader("Динамика показателей")
    if len(metrics_df) > 1:
        followers_ts = processor.prepare_time_series(metrics_df, 'followers', resample_freq='D')
        if not followers_ts.empty and len(followers_ts) > 1:
            chart = ChartBuilder.line_chart(
                followers_ts,
                x='collected_at',
                y='followers',
                title='Динамика подписчиков',
                y_label='Подписчики',
                color=PLATFORM_COLORS['telegram']
            )
            st.plotly_chart(chart, use_container_width=True)
    if len(metrics_df) > 1 and 'engagement_rate' in metrics_df.columns:
        er_ts = processor.prepare_time_series(metrics_df, 'engagement_rate', resample_freq='D')
        if not er_ts.empty and len(er_ts) > 1:
            chart = ChartBuilder.line_chart(
                er_ts,
                x='collected_at',
                y='engagement_rate',
                title='Динамика вовлеченности (ERR)',
                y_label='ER %',
                color=PLATFORM_COLORS['telegram']
            )
            st.plotly_chart(chart, use_container_width=True)
    if len(metrics_df) > 1 and 'avg_views' in metrics_df.columns:
        views_ts = processor.prepare_time_series(metrics_df, 'avg_views', resample_freq='D')
        if not views_ts.empty and len(views_ts) > 1:
            chart = ChartBuilder.line_chart(
                views_ts,
                x='collected_at',
                y='avg_views',
                title='Динамика средних просмотров',
                y_label='Просмотры',
                color=PLATFORM_COLORS['telegram']
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
            color=PLATFORM_COLORS['telegram']
        )
        st.plotly_chart(chart, use_container_width=True)
        if 'engagement_rate' in latest_sorted.columns:
            er_sorted = latest_df.sort_values('engagement_rate', ascending=True)
            chart = ChartBuilder.bar_chart(
                er_sorted,
                x='engagement_rate',
                y='display_name' if 'display_name' in er_sorted.columns else 'account_id',
                title='Вовлеченность по аккаунтам',
                x_label='ER %',
                y_label='Аккаунт',
                color=PLATFORM_COLORS['telegram']
            )
            st.plotly_chart(chart, use_container_width=True)
        if 'avg_views' in latest_sorted.columns:
            views_sorted = latest_df.sort_values('avg_views', ascending=True)
            chart = ChartBuilder.bar_chart(
                views_sorted,
                x='avg_views',
                y='display_name' if 'display_name' in latest_sorted.columns else 'account_id',
                title='Средние просмотры по аккаунтам',
                x_label='Средние просмотры',
                y_label='Аккаунт',
                color=PLATFORM_COLORS['telegram']
            )
            st.plotly_chart(chart, use_container_width=True)
    else:
        st.info("Выберите 'Все аккаунты' для сравнения")
    st.markdown("---")
    st.subheader("Последние метрики")
    render_metrics_table(latest_df)
with tab3:
    st.subheader("Топ посты по просмотрам")
    top_posts_by_views = []
    if not latest_df.empty and 'extra_data' in latest_df.columns:
        extra_data = latest_df.iloc[0]['extra_data'] if latest_df.iloc[0]['extra_data'] else {}
        top_posts_by_views = extra_data.get('top_posts_by_views', [])
    if top_posts_by_views:
        posts_data = []
        for idx, post in enumerate(top_posts_by_views, 1):
            posts_data.append({
                'Место': idx,
                'ID': post.get('id', 'N/A'),
                'Дата': post.get('date', '')[:10],
                'Текст': post.get('text', '')[:50] + '...' if len(post.get('text', '')) > 50 else post.get('text', ''),
                'Просмотры': post.get('views', 0),
                'Реакции': post.get('reactions', 0),
                'Репосты': post.get('forwards', 0)
            })
        df_posts = pd.DataFrame(posts_data)
        st.dataframe(df_posts, use_container_width=True)
    else:
        st.info("Нет данных о топ постах")
with tab4:
    st.subheader("Анализ реакций")
    reactions_breakdown = {}
    if not latest_df.empty and 'extra_data' in latest_df.columns:
        extra_data = latest_df.iloc[0]['extra_data'] if latest_df.iloc[0]['extra_data'] else {}
        reactions_breakdown = extra_data.get('reactions_breakdown', {})
    if reactions_breakdown:
        col1, col2 = st.columns(2)
        with col1:
            reaction_names = list(reactions_breakdown.keys())
            reaction_counts = list(reactions_breakdown.values())
            fig = go.Figure(data=[go.Pie(labels=reaction_names, values=reaction_counts, hole=.3)])
            fig.update_layout(title_text="Распределение реакций", height=400)
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            df_reactions = pd.DataFrame(list(reactions_breakdown.items()), columns=['Реакция', 'Количество'])
            df_reactions = df_reactions.sort_values('Количество', ascending=True)
            fig = px.bar(df_reactions, x='Количество', y='Реакция', orientation='h',
                         title='Количество по типам реакций',
                         color_discrete_sequence=[PLATFORM_COLORS['telegram']])
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        st.subheader("Таблица реакций")
        df_reactions_full = pd.DataFrame(list(reactions_breakdown.items()), columns=['Реакция', 'Количество'])
        df_reactions_full = df_reactions_full.sort_values(by='Количество', ascending=False)
        st.dataframe(df_reactions_full, use_container_width=True)
    else:
        st.info("Нет данных о реакциях")
with tab5:
    st.subheader("Управление аккаунтами")
    def toggle_account_status(account_id: str, new_status: bool):
        try:
            client = get_api_client()
            client.update_account_status(account_id, new_status)
            clear_all_caches()
            st.success(f"✅ Статус аккаунта обновлен")
        except Exception as e:
            st.error(f"⚠️ Ошибка обновления: {e}")
    if telegram_accounts:
        for account in telegram_accounts:
            render_account_card(account, on_toggle=toggle_account_status)
    else:
        st.info("Нет аккаунтов для отображения")
st.markdown("---")
st.caption(f"Последнее обновление: {datetime.now().strftime('%d.%m.%Y %H:%M')}")
