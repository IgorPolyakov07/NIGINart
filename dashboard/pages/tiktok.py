import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import Optional
from dashboard.config import PAGE_TITLE, PAGE_ICON
from dashboard.utils.session_state import init_session_state
from dashboard.utils.constants import PLATFORM_COLORS
from dashboard.utils.formatters import format_compact, format_number, format_percent
from dashboard.components.filters import render_date_range_filter, render_account_filter
from dashboard.components.kpi_cards import render_kpi_card
from dashboard.components.charts import ChartBuilder
from dashboard.components.tables import render_metrics_table
from dashboard.services.cache_manager import (
    fetch_accounts_cached,
    fetch_metrics_cached,
    clear_all_caches
)
from dashboard.services.data_processor import MetricsProcessor
from dashboard.services.api_client import get_api_client
from src.services.tiktok.content_analyzer import TikTokContentAnalyzer
st.set_page_config(
    page_title=f"TikTok - {PAGE_TITLE}",
    page_icon="🎵",
    layout="wide"
)
init_session_state()
st.title("🎵 TikTok Analytics")
st.markdown("Аналитика TikTok аккаунтов через Display API + Marketing API")
query_params = st.query_params
if "oauth_success" in query_params and query_params["oauth_success"] == "true":
    st.success("✅ TikTok аккаунт успешно подключен!")
    st.balloons()
    st.query_params.clear()
if "oauth_error" in query_params:
    error_type = query_params["oauth_error"]
    error_messages = {
        "invalid_state": "❌ Ошибка безопасности: недействительный CSRF токен.",
        "tiktok_api_error": "❌ Ошибка TikTok API. Проверьте учетные данные.",
        "invalid_response": "❌ Неверный формат ответа от TikTok.",
        "unknown": "❌ Неизвестная ошибка при авторизации."
    }
    st.error(error_messages.get(error_type, f"❌ Ошибка OAuth: {error_type}"))
    st.query_params.clear()
st.markdown("---")
col1, col2 = st.columns([2, 2])
with col1:
    try:
        tiktok_accounts = fetch_accounts_cached(platform='tiktok')
    except Exception as e:
        st.error(f"⚠️ Ошибка загрузки аккаунтов: {e}")
        st.stop()
    if not tiktok_accounts:
        st.warning("⚠️ Нет подключенных TikTok аккаунтов")
        col_a, col_b = st.columns([1, 2])
        with col_a:
            if st.button("🔗 Подключить TikTok", type="primary", use_container_width=True):
                try:
                    client = get_api_client()
                    response = client.get("/api/v1/oauth/tiktok/start")
                    if response.status_code == 200:
                        data = response.json()
                        auth_url = data.get("authorization_url")
                        st.markdown(f"""
                        <a href="{auth_url}" target="_blank" style="
                            display: inline-block;
                            padding: 0.5rem 1rem;
                            background-color: #ff0050;
                            color: white;
                            text-decoration: none;
                            border-radius: 0.25rem;
                            font-weight: 600;
                        ">🎵 Авторизовать TikTok</a>
                        """, unsafe_allow_html=True)
                    else:
                        st.error(f"⚠️ Ошибка: {response.text}")
                except Exception as e:
                    st.error(f"⚠️ Ошибка подключения: {e}")
        with col_b:
            st.info("""
            **Подключите аккаунт для просмотра:**
            - Динамика подписчиков
            - Статистика видео
            - Рекламные метрики (при наличии Business Account)
            - Демография аудитории
            """)
        st.stop()
    selected_account_id = render_account_filter(tiktok_accounts)
with col2:
    start_date, end_date = render_date_range_filter()
try:
    with st.spinner("Загрузка метрик..."):
        metrics_df = fetch_metrics_cached(
            platform='tiktok',
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
    - Запустить сбор данных через API
    - Расширить временной диапазон
    """)
    st.stop()
data_points = len(metrics_df)
if data_points == 1:
    st.warning("⚠️ Собрана только 1 точка данных. Для визуализации трендов запустите сбор несколько раз.")
elif data_points < 5:
    st.info(f"📊 Собрано {data_points} точек данных. Рекомендуется минимум 5 для анализа трендов.")
def calculate_pct_change(current: float, previous: float) -> Optional[float]:
    if previous is None or previous == 0:
        return None
    return ((current - previous) / abs(previous)) * 100
processor = MetricsProcessor()
latest_df = processor.aggregate_by_account(metrics_df)
current_followers = int(latest_df['followers'].sum())
current_videos = int(latest_df['posts_count'].sum())
current_total_views = int(latest_df['total_views'].sum())
current_engagement = float(latest_df['engagement_rate'].mean())
period_length = (end_date - start_date).days
if period_length > 0:
    prev_start = start_date - timedelta(days=period_length)
    prev_end = start_date
    try:
        prev_metrics_df = fetch_metrics_cached(
            platform='tiktok',
            start_date=prev_start,
            end_date=prev_end,
            account_id=None if selected_account_id == 'all' else selected_account_id
        )
        if not prev_metrics_df.empty:
            prev_latest = processor.aggregate_by_account(prev_metrics_df)
            prev_followers = int(prev_latest['followers'].sum())
            prev_videos = int(prev_latest['posts_count'].sum())
            prev_total_views = int(prev_latest['total_views'].sum())
            prev_engagement = float(prev_latest['engagement_rate'].mean())
            delta_followers = current_followers - prev_followers
            delta_videos = current_videos - prev_videos
            delta_views = current_total_views - prev_total_views
            delta_engagement = current_engagement - prev_engagement
        else:
            delta_followers = delta_videos = delta_views = delta_engagement = None
    except:
        delta_followers = delta_videos = delta_views = delta_engagement = None
else:
    delta_followers = delta_videos = delta_views = delta_engagement = None
st.markdown("---")
st.subheader("Ключевые показатели")
if not latest_df.empty and 'collected_at' in latest_df.columns:
    last_collection = latest_df['collected_at'].max()
    last_collection_naive = last_collection.replace(tzinfo=None) if hasattr(last_collection, 'tzinfo') and last_collection.tzinfo else last_collection
    hours_ago = (datetime.now() - last_collection_naive).total_seconds() / 3600
    if hours_ago > 24:
        st.warning(f"⚠️ Последний сбор был {hours_ago:.1f} часов назад. Данные могут быть устаревшими.")
    else:
        st.caption(f"📅 Последний сбор: {last_collection.strftime('%d.%m.%Y %H:%M')} ({hours_ago:.1f}ч назад)")
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
        "Вовлеченность",
        current_engagement,
        delta=delta_engagement,
        format_type='percent'
    )
with col3:
    render_kpi_card(
        "Всего видео",
        current_videos,
        delta=delta_videos,
        format_type='number'
    )
with col4:
    render_kpi_card(
        "Просмотры (всего)",
        current_total_views,
        delta=delta_views,
        format_type='compact'
    )
st.markdown("---")
tab1, tab2, tab3, tab4 = st.tabs([
    "📈 Динамика",
    "🎬 Видео",
    "📢 Реклама",
    "🔍 Аналитика контента"
])
with tab1:
    st.subheader("Динамика показателей")
    if len(metrics_df) == 0:
        st.warning("📊 Нет данных для отображения. Запустите сбор метрик.")
    else:
        followers_ts = processor.prepare_time_series(metrics_df, 'followers', resample_freq='D')
        if not followers_ts.empty:
            chart = ChartBuilder.line_chart(
                followers_ts,
                x='collected_at',
                y='followers',
                title='Динамика подписчиков',
                y_label='Подписчики',
                color=PLATFORM_COLORS.get('tiktok', '#EE1D52')
            )
            st.plotly_chart(chart, use_container_width=True)
        st.subheader("📊 Прирост подписчиков")
        growth_df = processor.calculate_growth(metrics_df, 'followers')
        if 'followers_change' not in growth_df.columns or growth_df['followers_change'].isna().all():
            st.info("Недостаточно данных для расчета прироста подписчиков. Требуется минимум 2 точки данных.")
        else:
            valid_growth = growth_df['followers_change'].dropna()
            if not valid_growth.empty:
                avg_growth = valid_growth.mean()
                max_growth = valid_growth.max()
                min_growth = valid_growth.min()
                positive_days_pct = (valid_growth > 0).sum() / len(valid_growth) * 100
                best_day_date = growth_df.loc[growth_df['followers_change'] == max_growth, 'collected_at'].iloc[0] if max_growth in valid_growth.values else None
                worst_day_date = growth_df.loc[growth_df['followers_change'] == min_growth, 'collected_at'].iloc[0] if min_growth in valid_growth.values else None
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Средний прирост", format_number(avg_growth))
                with col2:
                    st.metric(
                        "Лучший день",
                        format_number(max_growth),
                        delta=best_day_date.strftime('%d.%m.%Y') if best_day_date else None
                    )
                with col3:
                    st.metric(
                        "Худший день",
                        format_number(min_growth),
                        delta=worst_day_date.strftime('%d.%m.%Y') if worst_day_date else None
                    )
                with col4:
                    st.metric("Дней с ростом", f"{positive_days_pct:.1f}%")
                growth_ts = processor.prepare_time_series(growth_df, 'followers_change', resample_freq='D')
                if not growth_ts.empty:
                    chart = ChartBuilder.line_chart(
                        growth_ts,
                        x='collected_at',
                        y='followers_change',
                        title='Ежедневный прирост подписчиков',
                        y_label='Изменение подписчиков',
                        color=PLATFORM_COLORS.get('tiktok', '#EE1D52')
                    )
                    chart.add_hline(
                        y=0,
                        line_dash="dash",
                        line_color="gray",
                        opacity=0.5
                    )
                    st.plotly_chart(chart, use_container_width=True)
        if 'engagement_rate' in metrics_df.columns:
            er_ts = processor.prepare_time_series(metrics_df, 'engagement_rate', resample_freq='D')
            if not er_ts.empty:
                chart = ChartBuilder.line_chart(
                    er_ts,
                    x='collected_at',
                    y='engagement_rate',
                    title='Динамика вовлеченности',
                    y_label='ER %',
                    color=PLATFORM_COLORS.get('tiktok', '#EE1D52')
                )
                st.plotly_chart(chart, use_container_width=True)
        if 'total_views' in metrics_df.columns:
            views_ts = processor.prepare_time_series(metrics_df, 'total_views', resample_freq='D')
            if not views_ts.empty:
                chart = ChartBuilder.line_chart(
                    views_ts,
                    x='collected_at',
                    y='total_views',
                    title='Динамика просмотров',
                    y_label='Просмотры',
                    color=PLATFORM_COLORS.get('tiktok', '#EE1D52')
                )
                st.plotly_chart(chart, use_container_width=True)
with tab2:
    st.subheader("🎬 Топ видео")
    if not latest_df.empty and 'recent_videos' in latest_df.columns:
        if selected_account_id != 'all':
            account_row = latest_df[latest_df.index == selected_account_id]
        else:
            account_row = latest_df.iloc[[0]]
        if not account_row.empty:
            recent_videos = account_row.iloc[0].get('recent_videos')
            if isinstance(recent_videos, list) and len(recent_videos) > 0:
                col_filter1, col_filter2 = st.columns(2)
                with col_filter1:
                    sort_options = {
                        "Просмотрам": "view_count",
                        "Лайкам": "like_count",
                        "Комментариям": "comment_count",
                        "Репостам": "share_count",
                        "Вовлеченности": "engagement"
                    }
                    selected_sort_label = st.selectbox(
                        "Сортировать по",
                        options=list(sort_options.keys()),
                        index=0,
                        key='tiktok_videos_sort'
                    )
                    sort_field = sort_options[selected_sort_label]
                with col_filter2:
                    max_videos = len(recent_videos)
                    default_count = min(10, max_videos)
                    video_count = st.number_input(
                        "Количество видео",
                        min_value=1,
                        max_value=max_videos,
                        value=default_count,
                        step=1,
                        key='tiktok_videos_count'
                    )
                data = []
                for video in recent_videos:
                    views = video.get('view_count', 0)
                    likes = video.get('like_count', 0)
                    comments = video.get('comment_count', 0)
                    shares = video.get('share_count', 0)
                    engagement_rate = ((likes + comments + shares) / max(views, 1) * 100)
                    data.append({
                        'video_id': video.get('video_id', ''),
                        'title': video.get('title', 'Без названия'),
                        'cover': video.get('cover_image_url', ''),
                        'url': video.get('share_url', '#'),
                        'views': views,
                        'likes': likes,
                        'comments': comments,
                        'shares': shares,
                        'engagement': engagement_rate,
                        'duration': video.get('duration', 0)
                    })
                videos_df = pd.DataFrame(data)
                if sort_field == 'engagement':
                    videos_df = videos_df.sort_values('engagement', ascending=False)
                else:
                    videos_df = videos_df.sort_values(sort_field, ascending=False)
                top_videos = videos_df.head(video_count)
                for i, video in enumerate(top_videos.to_dict('records'), 1):
                    with st.expander(f"{i}. {video['title'][:60]}{'...' if len(video['title']) > 60 else ''}", expanded=(i <= 3)):
                        col1, col2 = st.columns([1, 2])
                        with col1:
                            if video['cover']:
                                st.image(video['cover'], width=200)
                        with col2:
                            st.write(f"**👁 Просмотры:** {format_compact(video['views'])}")
                            st.write(f"**❤️ Лайки:** {format_compact(video['likes'])}")
                            st.write(f"**💬 Комментарии:** {format_compact(video['comments'])}")
                            st.write(f"**🔄 Репосты:** {format_compact(video['shares'])}")
                            st.write(f"**📊 Engagement:** {video['engagement']:.2f}%")
                            st.write(f"**⏱ Длительность:** {video['duration']}с")
                            if video['url'] != '#':
                                st.markdown(f"[🎵 Смотреть на TikTok]({video['url']})")
                st.markdown("---")
                st.markdown("#### Статистика выбранных видео")
                stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)
                with stat_col1:
                    st.metric("Всего просмотров", format_compact(int(top_videos['views'].sum())))
                with stat_col2:
                    st.metric("Средние просмотры", format_compact(int(top_videos['views'].mean())))
                with stat_col3:
                    st.metric("Средний ER", format_percent(top_videos['engagement'].mean()))
                with stat_col4:
                    st.metric("Всего лайков", format_compact(int(top_videos['likes'].sum())))
            else:
                st.info("📹 Нет данных о последних видео. Запустите сбор метрик.")
        else:
            st.info("📹 Выберите аккаунт для просмотра видео.")
    else:
        st.info("📹 Нет данных о последних видео. Запустите сбор метрик.")
with tab3:
    st.subheader("📢 Рекламные метрики")
    has_ads = False
    ads_data = None
    if not latest_df.empty and 'ads_metrics' in latest_df.columns:
        if selected_account_id != 'all':
            account_row = latest_df[latest_df.index == selected_account_id]
        else:
            account_row = latest_df.iloc[[0]]
        if not account_row.empty:
            ads_raw = account_row.iloc[0].get('ads_metrics')
            if ads_raw and isinstance(ads_raw, dict):
                has_ads = True
                ads_data = ads_raw
    if has_ads and ads_data:
        st.markdown("### Выберите период")
        selected_period = st.radio(
            "Период",
            options=['7d', '30d', '90d', 'lifetime'],
            index=1,
            horizontal=True,
            format_func=lambda x: {'7d': '7 дней', '30d': '30 дней', '90d': '90 дней', 'lifetime': 'Все время'}[x],
            key='tiktok_ads_period'
        )
        period_data = ads_data.get(selected_period, {})
        if period_data:
            st.markdown("---")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Расходы", f"${period_data.get('total_spend', 0):,.2f}")
            with col2:
                st.metric("Показы", f"{period_data.get('total_impressions', 0):,}")
            with col3:
                st.metric("Клики", f"{period_data.get('total_clicks', 0):,}")
            with col4:
                st.metric("CTR", f"{period_data.get('avg_ctr', 0):.2f}%")
            st.markdown("---")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("CPM", f"${period_data.get('avg_cpm', 0):.2f}")
            with col2:
                st.metric("Конверсии", f"{period_data.get('total_conversions', 0):,}")
            with col3:
                st.metric("Conversion Rate", f"{period_data.get('avg_conversion_rate', 0):.2f}%")
            with col4:
                st.metric("Кампаний", period_data.get('campaigns_count', 0))
            st.markdown("---")
            st.markdown("#### 🏆 Топ кампании")
            top_campaigns = period_data.get('top_campaigns', [])
            if top_campaigns:
                campaigns_data = []
                for campaign in top_campaigns[:5]:
                    campaigns_data.append({
                        "Название": campaign.get('campaign_name', 'Unnamed'),
                        "Цель": campaign.get('objective_type', 'N/A'),
                        "Бюджет": f"${campaign.get('budget', 0):,.2f}" if campaign.get('budget') else "—",
                        "Статус": campaign.get('status', 'UNKNOWN')
                    })
                campaigns_df = pd.DataFrame(campaigns_data)
                st.dataframe(campaigns_df, use_container_width=True, hide_index=True)
            else:
                st.info("Нет данных о кампаниях")
        if 'audience_insights' in ads_data:
            st.markdown("---")
            st.markdown("### 👥 Демография аудитории")
            audience = ads_data['audience_insights']
            col1, col2 = st.columns(2)
            with col1:
                gender_dist = audience.get('gender_distribution', {})
                if gender_dist:
                    st.markdown("#### Пол")
                    fig = px.pie(
                        values=list(gender_dist.values()),
                        names=[k.capitalize() for k in gender_dist.keys()],
                        color_discrete_sequence=['#69C9D0', '#EE1D52']
                    )
                    fig.update_layout(height=300)
                    st.plotly_chart(fig, use_container_width=True)
            with col2:
                age_dist = audience.get('age_distribution', {})
                if age_dist:
                    st.markdown("#### Возраст")
                    fig = px.bar(
                        x=list(age_dist.keys()),
                        y=[v * 100 for v in age_dist.values()],
                        labels={'x': 'Возрастная группа', 'y': 'Процент (%)'},
                        color_discrete_sequence=['#EE1D52']
                    )
                    fig.update_layout(height=300, showlegend=False)
                    st.plotly_chart(fig, use_container_width=True)
            top_countries = audience.get('top_countries', [])
            if top_countries:
                st.markdown("#### 🌍 Топ страны")
                countries_data = []
                for country in top_countries[:10]:
                    countries_data.append({
                        "Страна": country.get('country', 'N/A'),
                        "Процент": f"{country.get('percentage', 0) * 100:.1f}%"
                    })
                countries_df = pd.DataFrame(countries_data)
                st.dataframe(countries_df, use_container_width=True, hide_index=True)
            top_interests = audience.get('top_interests', [])
            if top_interests:
                st.markdown("#### 💡 Топ интересы")
                st.write(", ".join(top_interests[:15]))
    else:
        st.info("""
        💡 **Подключите TikTok Business Account для просмотра рекламных метрик**
        После подключения здесь будут отображаться:
        - Расходы на рекламу
        - Показы, клики, CTR
        - Топ кампании
        - Демография аудитории (пол, возраст, страны)
        - Интересы аудитории
        Рекламные метрики доступны за 4 периода: 7д, 30д, 90д, все время.
        """)
        if st.button("🔗 Подключить TikTok Ads"):
            try:
                client = get_api_client()
                response = client.get("/api/v1/oauth/tiktok/start")
                if response.status_code == 200:
                    data = response.json()
                    auth_url = data.get("authorization_url")
                    st.markdown(f"""
                    <a href="{auth_url}" target="_blank" style="
                        display: inline-block;
                        padding: 0.5rem 1rem;
                        background-color: #ff0050;
                        color: white;
                        text-decoration: none;
                        border-radius: 0.25rem;
                        font-weight: 600;
                    ">🎵 Авторизовать TikTok Business</a>
                    """, unsafe_allow_html=True)
                else:
                    st.error(f"⚠️ Ошибка: {response.text}")
            except Exception as e:
                st.error(f"⚠️ Ошибка: {e}")
with tab4:
    st.subheader("🔍 Аналитика контента")
    recent_videos_for_analysis = []
    if not latest_df.empty and 'recent_videos' in latest_df.columns:
        if selected_account_id != 'all':
            account_row = latest_df[latest_df.index == selected_account_id]
        else:
            account_row = latest_df.iloc[[0]]
        if not account_row.empty:
            videos_raw = account_row.iloc[0].get('recent_videos')
            if isinstance(videos_raw, list) and len(videos_raw) > 0:
                for video in videos_raw:
                    recent_videos_for_analysis.append({
                        'video_id': video.get('video_id', ''),
                        'title': video.get('title', ''),
                        'published_at': video.get('create_time', ''),
                        'views': video.get('view_count', 0),
                        'likes': video.get('like_count', 0),
                        'comments': video.get('comment_count', 0),
                        'shares': video.get('share_count', 0),
                        'duration': video.get('duration', 0),
                        'engagement_rate': ((video.get('like_count', 0) +
                                           video.get('comment_count', 0) +
                                           video.get('share_count', 0)) /
                                          max(video.get('view_count', 1), 1) * 100)
                    })
    if recent_videos_for_analysis:
        analyzer = TikTokContentAnalyzer(recent_videos_for_analysis)
        content_tab1, content_tab2, content_tab3, content_tab4 = st.tabs([
            "📌 Хэштеги",
            "⏰ Время публикации",
            "⏱ Длительность",
            "🔥 Вирусный контент"
        ])
        with content_tab1:
            _render_hashtag_analysis(analyzer)
        with content_tab2:
            _render_posting_patterns(analyzer)
        with content_tab3:
            _render_duration_analysis(analyzer)
        with content_tab4:
            _render_viral_content(analyzer)
    else:
        st.info("""
        📊 **Нет данных для анализа контента**
        Для анализа контента необходимы данные о последних видео аккаунта.
        Убедитесь что:
        - Выбран конкретный аккаунт (не "Все аккаунты")
        - Выполнен сбор метрик для этого аккаунта
        - У аккаунта есть опубликованные видео
        """)
def _render_hashtag_analysis(analyzer: TikTokContentAnalyzer):
    st.markdown("### 📌 Анализ хэштегов")
    st.markdown("Определение наиболее эффективных хэштегов по просмотрам и вовлеченности")
    result = analyzer.analyze_hashtags()
    if not result['success']:
        st.warning(f"⚠️ {result['message']}")
        return
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Уникальных хэштегов", result['total_unique_hashtags'])
    with col2:
        st.metric("Видео с хэштегами", result['videos_with_hashtags'])
    with col3:
        st.metric("Видео без хэштегов", result['videos_without_hashtags'])
    st.markdown("---")
    st.markdown("#### 🏆 Топ хэштеги")
    if result['hashtags']:
        hashtags_data = []
        trend_emoji = {
            'rising': '📈',
            'stable': '➡️',
            'declining': '📉',
            'insufficient_data': '❓'
        }
        for h in result['hashtags'][:15]:
            hashtags_data.append({
                'Хэштег': f"#{h['hashtag']}",
                'Использовано': h['count'],
                'Средние просмотры': format_compact(int(h['avg_views'])),
                'Средний ER': f"{h['avg_engagement']:.2f}%",
                'Тренд': f"{trend_emoji.get(h['trend'], '❓')} {h['trend'].capitalize()}"
            })
        hashtags_df = pd.DataFrame(hashtags_data)
        st.dataframe(hashtags_df, use_container_width=True, hide_index=True)
        st.markdown("---")
        st.markdown("#### 📊 Вовлеченность по хэштегам")
        top_10 = result['hashtags'][:10]
        chart_data = pd.DataFrame({
            'Хэштег': [f"#{h['hashtag']}" for h in top_10],
            'Engagement Rate': [h['avg_engagement'] for h in top_10]
        })
        chart = ChartBuilder.bar_chart(
            chart_data,
            x='Хэштег',
            y='Engagement Rate',
            title='Топ 10 хэштегов по вовлеченности',
            x_label='Хэштег',
            y_label='Средний ER (%)',
            color=PLATFORM_COLORS.get('tiktok', '#EE1D52')
        )
        st.plotly_chart(chart, use_container_width=True)
        st.markdown("---")
        st.markdown("#### 💡 Рекомендации")
        rising_hashtags = [h for h in result['hashtags'] if h['trend'] == 'rising']
        if rising_hashtags:
            st.success(f"📈 **Растущие хэштеги:** {', '.join(['#' + h['hashtag'] for h in rising_hashtags[:5]])}")
        declining_hashtags = [h for h in result['hashtags'] if h['trend'] == 'declining']
        if declining_hashtags:
            st.warning(f"📉 **Снижающиеся хэштеги:** {', '.join(['#' + h['hashtag'] for h in declining_hashtags[:5]])}")
        best_hashtag = result['hashtags'][0]
        st.info(f"🏆 **Лучший хэштег:** #{best_hashtag['hashtag']} "
                f"(использован {best_hashtag['count']} раз, средний ER {best_hashtag['avg_engagement']:.2f}%)")
def _render_posting_patterns(analyzer: TikTokContentAnalyzer):
    st.markdown("### ⏰ Оптимальное время публикации")
    st.markdown("Анализ эффективности публикаций по дням недели и времени суток")
    result = analyzer.analyze_posting_patterns()
    if not result['success']:
        st.warning(f"⚠️ {result['message']}")
        return
    st.metric("Оптимальная частота", result['optimal_frequency'])
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 📅 Лучшие дни недели")
        if result['best_days']:
            days_data = pd.DataFrame(result['best_days'][:7])
            chart = ChartBuilder.bar_chart(
                days_data,
                x='day',
                y='avg_engagement',
                title='Вовлеченность по дням недели',
                x_label='День',
                y_label='Средний ER (%)',
                color=PLATFORM_COLORS.get('tiktok', '#EE1D52')
            )
            chart.update_layout(height=350)
            st.plotly_chart(chart, use_container_width=True)
            st.markdown("**Топ 3 дня:**")
            for i, day in enumerate(result['best_days'][:3], 1):
                st.write(f"{i}. **{day['day']}** - {day['avg_engagement']:.2f}% ER ({day['video_count']} видео)")
    with col2:
        st.markdown("#### 🕐 Лучшие часы")
        if result['best_hours']:
            hours_data = pd.DataFrame(result['best_hours'][:24])
            hours_data['hour_label'] = hours_data['hour'].apply(lambda h: f"{h:02d}:00")
            chart = ChartBuilder.bar_chart(
                hours_data,
                x='hour_label',
                y='avg_engagement',
                title='Вовлеченность по часам',
                x_label='Час',
                y_label='Средний ER (%)',
                color=PLATFORM_COLORS.get('tiktok', '#EE1D52')
            )
            chart.update_layout(height=350, xaxis_tickangle=-45)
            st.plotly_chart(chart, use_container_width=True)
            st.markdown("**Топ 3 часа:**")
            for i, hour in enumerate(result['best_hours'][:3], 1):
                st.write(f"{i}. **{hour['hour']:02d}:00** - {hour['avg_engagement']:.2f}% ER ({hour['video_count']} видео)")
    st.markdown("---")
    st.markdown("#### 💡 Рекомендации")
    if result['best_days']:
        best_day = result['best_days'][0]
        st.success(f"📅 **Лучший день:** {best_day['day']} (ER {best_day['avg_engagement']:.2f}%)")
    if result['best_hours']:
        best_hour = result['best_hours'][0]
        st.success(f"🕐 **Лучший час:** {best_hour['hour']:02d}:00 (ER {best_hour['avg_engagement']:.2f}%)")
    st.info(f"📊 **Рекомендуемая частота:** {result['optimal_frequency']}")
def _render_duration_analysis(analyzer: TikTokContentAnalyzer):
    st.markdown("### ⏱ Анализ длительности видео")
    st.markdown("Определение оптимальной длительности видео для максимальной вовлеченности")
    result = analyzer.analyze_video_duration()
    if not result['success']:
        st.warning(f"⚠️ {result['message']}")
        return
    st.metric("Оптимальная длительность", result['optimal_duration'])
    st.markdown("---")
    st.markdown("#### 📊 Статистика по длительности")
    if result['duration_buckets']:
        buckets_data = []
        for bucket in result['duration_buckets']:
            buckets_data.append({
                'Длительность': bucket['bucket'],
                'Количество видео': bucket['video_count'],
                'Средние просмотры': format_compact(int(bucket['avg_views'])),
                'Средний ER': f"{bucket['avg_engagement']:.2f}%"
            })
        buckets_df = pd.DataFrame(buckets_data)
        st.dataframe(buckets_df, use_container_width=True, hide_index=True)
        st.markdown("---")
        st.markdown("#### 📈 Вовлеченность по длительности")
        chart_data = pd.DataFrame({
            'Длительность': [b['bucket'] for b in result['duration_buckets']],
            'Engagement Rate': [b['avg_engagement'] for b in result['duration_buckets']]
        })
        chart = ChartBuilder.bar_chart(
            chart_data,
            x='Длительность',
            y='Engagement Rate',
            title='Вовлеченность по диапазонам длительности',
            x_label='Диапазон',
            y_label='Средний ER (%)',
            color=PLATFORM_COLORS.get('tiktok', '#EE1D52')
        )
        st.plotly_chart(chart, use_container_width=True)
        st.markdown("---")
        st.markdown("#### 💡 Рекомендации")
        optimal_bucket = result['duration_buckets'][0]
        st.success(f"🎯 **Рекомендуемая длительность:** {optimal_bucket['bucket']} "
                  f"(ER {optimal_bucket['avg_engagement']:.2f}%)")
        if len(result['duration_buckets']) > 1:
            worst_bucket = result['duration_buckets'][-1]
            st.info(f"⚠️ **Наименее эффективная длительность:** {worst_bucket['bucket']} "
                   f"(ER {worst_bucket['avg_engagement']:.2f}%)")
def _render_viral_content(analyzer: TikTokContentAnalyzer):
    st.markdown("### 🔥 Вирусный контент")
    st.markdown("Определение видео с исключительно высокими показателями")
    threshold_multiplier = st.slider(
        "Порог вирусности (множитель средних просмотров)",
        min_value=1.5,
        max_value=5.0,
        value=3.0,
        step=0.5,
        help="Видео считается вирусным, если просмотры превышают среднее в N раз"
    )
    result = analyzer.detect_viral_content(threshold_multiplier=threshold_multiplier)
    if not result['success']:
        st.warning(f"⚠️ {result['message']}")
        return
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Порог просмотров", format_compact(int(result['threshold_views'])))
    with col2:
        st.metric("Вирусных видео", len(result['viral_videos']))
    with col3:
        st.metric("% вирусных", f"{result['viral_rate']:.1f}%")
    st.markdown("---")
    if result['viral_videos']:
        st.markdown("#### 🔥 Вирусные видео")
        for i, video in enumerate(result['viral_videos'], 1):
            with st.expander(f"{i}. {video['title'][:60]}{'...' if len(video['title']) > 60 else ''}", expanded=(i <= 3)):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Просмотры", format_compact(video['views']))
                    st.metric("Множитель", f"{video['multiplier']:.1f}x")
                with col2:
                    st.metric("Engagement Rate", f"{video['engagement_rate']:.2f}%")
                with col3:
                    if video.get('published_at'):
                        st.write(f"**Опубликовано:** {video['published_at'][:10]}")
        st.markdown("---")
        st.markdown("#### 💡 Рекомендации")
        if result['viral_rate'] > 20:
            st.success(f"🎉 **Отличный результат!** {result['viral_rate']:.1f}% видео стали вирусными")
        elif result['viral_rate'] > 10:
            st.info(f"👍 **Хороший результат!** {result['viral_rate']:.1f}% видео стали вирусными")
        else:
            st.warning(f"💡 Вирусных видео мало ({result['viral_rate']:.1f}%). "
                      f"Попробуйте проанализировать хэштеги и время публикации вирусных видео.")
    else:
        st.info(f"ℹ️ Нет видео с просмотрами выше {format_compact(int(result['threshold_views']))}. "
               f"Попробуйте уменьшить порог вирусности.")
st.markdown("---")
st.caption(f"Последнее обновление: {datetime.now().strftime('%d.%m.%Y %H:%M')}")
st.caption("💡 TikTok Display API OAuth 2.0 + Marketing API | Token encryption: Fernet AES-128")
