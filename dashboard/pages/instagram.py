import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import Optional, Dict
from uuid import UUID
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
st.set_page_config(
    page_title=f"Instagram - {PAGE_TITLE}",
    page_icon="📸",
    layout="wide"
)
init_session_state()
st.title("📸 Instagram Analytics")
st.markdown("Аналитика Instagram Business аккаунтов через Facebook Graph API")
query_params = st.query_params
if "oauth_success" in query_params and query_params["oauth_success"] == "true":
    st.success("✅ Instagram аккаунт успешно подключен!")
    st.balloons()
    st.query_params.clear()
if "oauth_error" in query_params:
    error_type = query_params["oauth_error"]
    error_messages = {
        "invalid_state": "❌ Ошибка безопасности: недействительный CSRF токен.",
        "facebook_api_error": "❌ Ошибка Facebook API. Проверьте учетные данные.",
        "invalid_response": "❌ Неверный формат ответа от Facebook.",
        "no_instagram_pages": "❌ У вас нет Facebook Pages с подключенным Instagram Business Account.",
        "unknown": "❌ Неизвестная ошибка при авторизации."
    }
    st.error(error_messages.get(error_type, f"❌ Ошибка OAuth: {error_type}"))
    st.query_params.clear()
st.markdown("---")
col1, col2 = st.columns([2, 2])
with col1:
    try:
        instagram_accounts = fetch_accounts_cached(platform='instagram')
    except Exception as e:
        st.error(f"⚠️ Ошибка загрузки аккаунтов: {e}")
        st.stop()
    if not instagram_accounts:
        st.warning("⚠️ Нет подключенных Instagram Business аккаунтов")
        col_a, col_b = st.columns([1, 2])
        with col_a:
            if st.button("🔗 Подключить Instagram", type="primary", use_container_width=True):
                try:
                    client = get_api_client()
                    response = client.get("/api/v1/oauth/instagram/start")
                    if response.status_code == 200:
                        data = response.json()
                        auth_url = data.get("authorization_url")
                        st.markdown(f"""
                        <a href="{auth_url}" target="_blank" style="
                            display: inline-block;
                            padding: 0.5rem 1rem;
                            background-color: #e1306c;
                            color: white;
                            text-decoration: none;
                            border-radius: 0.25rem;
                            font-weight: 600;
                        ">📸 Авторизовать через Facebook</a>
                        """, unsafe_allow_html=True)
                    else:
                        st.error(f"⚠️ Ошибка: {response.text}")
                except Exception as e:
                    st.error(f"⚠️ Ошибка подключения: {e}")
        with col_b:
            st.info("""
            **Подключите аккаунт для просмотра:**
            - Динамика подписчиков
            - Статистика постов (reach, impressions, saved)
            - Engagement rate
            - Демография аудитории
            **Требования:**
            - Instagram Business Account
            - Подключен к Facebook Page
            - Доступ к Business Manager
            """)
        st.stop()
    selected_account_id = render_account_filter(instagram_accounts)
with col2:
    start_date, end_date = render_date_range_filter()
try:
    with st.spinner("Загрузка метрик..."):
        metrics_df = fetch_metrics_cached(
            platform='instagram',
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
current_posts = int(latest_df['posts_count'].sum())
current_total_impressions = int(latest_df['total_views'].sum())
current_engagement = float(latest_df['engagement_rate'].mean())
period_length = (end_date - start_date).days
if period_length > 0:
    prev_start = start_date - timedelta(days=period_length)
    prev_end = start_date
    try:
        prev_metrics_df = fetch_metrics_cached(
            platform='instagram',
            start_date=prev_start,
            end_date=prev_end,
            account_id=None if selected_account_id == 'all' else selected_account_id
        )
        if not prev_metrics_df.empty:
            prev_latest = processor.aggregate_by_account(prev_metrics_df)
            prev_followers = int(prev_latest['followers'].sum())
            prev_posts = int(prev_latest['posts_count'].sum())
            prev_total_impressions = int(prev_latest['total_views'].sum())
            prev_engagement = float(prev_latest['engagement_rate'].mean())
            delta_followers = current_followers - prev_followers
            delta_posts = current_posts - prev_posts
            delta_impressions = current_total_impressions - prev_total_impressions
            delta_engagement = current_engagement - prev_engagement
        else:
            delta_followers = delta_posts = delta_impressions = delta_engagement = None
    except:
        delta_followers = delta_posts = delta_impressions = delta_engagement = None
else:
    delta_followers = delta_posts = delta_impressions = delta_engagement = None
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
        "Всего постов",
        current_posts,
        delta=delta_posts,
        format_type='number'
    )
with col4:
    render_kpi_card(
        "Impressions",
        current_total_impressions,
        delta=delta_impressions,
        format_type='compact'
    )
st.markdown("---")
tab1, tab2, tab3, tab4 = st.tabs([
    "📈 Динамика",
    "📸 Посты",
    "📢 Реклама",
    "🔍 Аналитика контента"
])
with tab1:
    st.subheader("📊 Динамика метрик")
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Подписчики")
        followers_ts = processor.prepare_time_series(metrics_df, 'followers', resample_freq='D')
        fig_followers = ChartBuilder.line_chart(
            followers_ts,
            x='collected_at',
            y='followers',
            title='Динамика подписчиков',
            y_label='Подписчики',
            color=PLATFORM_COLORS['instagram']
        )
        st.plotly_chart(fig_followers, use_container_width=True)
    with col2:
        st.markdown("#### Вовлеченность")
        er_ts = processor.prepare_time_series(metrics_df, 'engagement_rate', resample_freq='D')
        fig_engagement = ChartBuilder.line_chart(
            er_ts,
            x='collected_at',
            y='engagement_rate',
            title='Engagement Rate (%)',
            y_label='ER %',
            color=PLATFORM_COLORS['instagram']
        )
        st.plotly_chart(fig_engagement, use_container_width=True)
    col3, col4 = st.columns(2)
    with col3:
        st.markdown("#### Посты")
        posts_ts = processor.prepare_time_series(metrics_df, 'posts_count', resample_freq='D')
        fig_posts = ChartBuilder.line_chart(
            posts_ts,
            x='collected_at',
            y='posts_count',
            title='Количество постов',
            y_label='Постов',
            color=PLATFORM_COLORS['instagram']
        )
        st.plotly_chart(fig_posts, use_container_width=True)
    with col4:
        st.markdown("#### Просмотры")
        if 'total_views' in metrics_df.columns and metrics_df['total_views'].notna().any():
            views_ts = processor.prepare_time_series(metrics_df, 'total_views', resample_freq='D')
            fig_views = ChartBuilder.line_chart(
                views_ts,
                x='collected_at',
                y='total_views',
                title='Total Views',
                y_label='Просмотры',
                color=PLATFORM_COLORS['instagram']
            )
            st.plotly_chart(fig_views, use_container_width=True)
        else:
            st.info("Данные о просмотрах недоступны для Basic Display API")
with tab2:
    st.subheader("📸 Последние посты")
    if not latest_df.empty and 'extra_data' in latest_df.columns:
        extra_data = latest_df.iloc[0].get('extra_data', {})
        recent_media = extra_data.get('recent_media', [])
        if recent_media:
            col_sort, col_limit = st.columns([2, 1])
            with col_sort:
                sort_by = st.selectbox(
                    "Сортировать по",
                    options=['saved', 'reach', 'likes', 'engagement_rate', 'comments', 'impressions'],
                    format_func=lambda x: {
                        'saved': '💾 Сохранения (Purchase Intent)',
                        'reach': '👁️ Охват',
                        'likes': '❤️ Лайки',
                        'engagement_rate': '📈 Engagement Rate',
                        'comments': '💬 Комментарии',
                        'impressions': '👀 Impressions'
                    }[x]
                )
            with col_limit:
                limit = st.slider("Показать постов", 1, min(25, len(recent_media)), min(10, len(recent_media)))
            sorted_media = sorted(recent_media, key=lambda x: x.get(sort_by, 0), reverse=True)[:limit]
            for i, post in enumerate(sorted_media, 1):
                _render_media_card(post, i, expanded=(i <= 3))
            st.markdown("---")
            st.markdown("**Статистика отображаемых постов:**")
            total_saves = sum(p.get('saved', 0) for p in sorted_media)
            avg_reach = sum(p.get('reach', 0) for p in sorted_media) / len(sorted_media)
            avg_er = sum(p.get('engagement_rate', 0) for p in sorted_media) / len(sorted_media)
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Всего Saves", f"{total_saves:,}")
            col2.metric("Ср. Reach", format_compact(avg_reach))
            col3.metric("Ср. ER", f"{avg_er:.1f}%")
            col4.metric("Постов", len(sorted_media))
        else:
            st.info("📊 Нет данных о постах")
    else:
        st.info("📊 Нет данных о постах")
with tab3:
    st.subheader("📢 Реклама Instagram")
    st.info("""
    **Статус:** Функция в разработке
    Instagram Graph API не предоставляет прямой доступ к рекламным метрикам.
    Для доступа к данным Instagram Ads требуется:
    - Отдельное подключение к Facebook Marketing API
    - Разрешения Ad Account Admin
    - Business Manager настройки
    Обратитесь к администратору для подключения рекламного аккаунта.
    """)
with tab4:
    st.subheader("🎯 Контент-аналитика: Что стреляет?")
    st.markdown("""
    **Fashion-focused контент анализ для бренда NIGINart:**
    - 🔥 Топ посты по сохранениям (покупательский интерес)
    - 📸 Сравнение форматов: Reels vs Posts vs Карусели
    - #️⃣ Эффективность хэштегов
    - ⏰ Оптимальное время для публикации (MSK)
    - ✍️ Анализ подписей и CTA
    """)
    col_analyze, col_info = st.columns([1, 3])
    analysis = None
    with col_analyze:
        analyze_button = st.button("📊 Запустить анализ контента", type="primary", use_container_width=True)
    with col_info:
        st.caption("💡 Анализ последних 30 дней контента для понимания, какие посты приводят к покупкам")
    if analyze_button:
        if selected_account_id == 'all':
            st.warning("⚠️ Выберите конкретный аккаунт для анализа контента")
        else:
            with st.spinner("Анализируем контент..."):
                try:
                    client = get_api_client()
                    response = client.post(
                        f"/api/v1/instagram/{selected_account_id}/analyze-content",
                        params={"days": 30, "include_stories": False}
                    )
                    if response.status_code == 200:
                        analysis = response.json()
                        st.success(f"✅ Анализ завершен! Проанализировано {analysis['posts_analyzed']} постов")
                    else:
                        st.error(f"⚠️ Ошибка анализа: {response.text}")
                except Exception as e:
                    st.error(f"⚠️ Ошибка запроса: {e}")
    if analysis:
        analysis_tab1, analysis_tab2, analysis_tab3, analysis_tab4, analysis_tab5 = st.tabs([
            "🔥 Топ посты",
            "📸 Форматы",
            "#️⃣ Хэштеги",
            "⏰ Время",
            "💡 Инсайты"
        ])
        with analysis_tab1:
            st.markdown("### 🔥 Топ посты по сохранениям (покупательский интерес)")
            top_posts = analysis.get('top_posts_by_saves', [])
            if top_posts:
                for i, post in enumerate(top_posts[:5], 1):
                    with st.container():
                        col_rank, col_content = st.columns([1, 10])
                        with col_rank:
                            st.markdown(f"### #{i}")
                        with col_content:
                            caption = post.get('caption', 'Без описания')
                            caption_preview = caption[:100] + '...' if len(caption) > 100 else caption
                            st.markdown(f"**{post.get('media_type')}** - {caption_preview}")
                            col_saves, col_reach, col_eng = st.columns(3)
                            with col_saves:
                                st.metric("💾 Сохранения", post.get('saved', 0))
                            with col_reach:
                                st.metric("👁️ Reach", format_compact(post.get('reach', 0)))
                            with col_eng:
                                st.metric("📈 Engagement", f"{post.get('engagement_rate', 0):.1f}%")
                        st.markdown("---")
            else:
                st.info("Нет данных о топ постах")
        with analysis_tab2:
            st.markdown("### 📸 Сравнение форматов контента")
            content_types = analysis.get('content_types', {})
            if content_types.get('success'):
                types_data = content_types.get('types', [])
                if types_data:
                    types_df = pd.DataFrame(types_data)
                    fig_types = px.bar(
                        types_df,
                        x='type',
                        y='save_rate',
                        title='Save Rate по форматам (%)',
                        labels={'type': 'Формат', 'save_rate': 'Save Rate %'},
                        color='save_rate',
                        color_continuous_scale='Viridis'
                    )
                    st.plotly_chart(fig_types, use_container_width=True)
                    st.markdown("**Детальная статистика:**")
                    display_types = types_df[[
                        'type', 'count', 'avg_saves', 'avg_reach', 'save_rate'
                    ]].copy()
                    display_types.columns = [
                        'Формат', 'Кол-во', 'Avg Saves', 'Avg Reach', 'Save Rate %'
                    ]
                    st.dataframe(display_types, use_container_width=True, hide_index=True)
                    st.success(f"✨ {content_types.get('recommendation', '')}")
            else:
                st.info(content_types.get('message', 'Недостаточно данных'))
        with analysis_tab3:
            st.markdown("### #️⃣ Анализ хэштегов")
            hashtags = analysis.get('hashtags', [])
            if hashtags:
                hashtags_df = pd.DataFrame(hashtags[:15])
                st.markdown("**Топ хэштеги по Save Rate:**")
                display_hashtags = hashtags_df[[
                    'hashtag', 'category', 'posts_count', 'avg_saves', 'save_rate'
                ]].copy()
                display_hashtags.columns = [
                    'Хэштег', 'Категория', 'Постов', 'Avg Saves', 'Save Rate %'
                ]
                st.dataframe(display_hashtags, use_container_width=True, hide_index=True)
                st.markdown("---")
                st.markdown("**Распределение по категориям:**")
                category_counts = hashtags_df.groupby('category').size().reset_index(name='count')
                fig_categories = px.pie(
                    category_counts,
                    values='count',
                    names='category',
                    title='Хэштеги по категориям'
                )
                st.plotly_chart(fig_categories, use_container_width=True)
            else:
                st.info("Недостаточно данных о хэштегах")
        with analysis_tab4:
            st.markdown("### ⏰ Оптимальное время для публикации (MSK)")
            posting_patterns = analysis.get('posting_patterns', {})
            if posting_patterns.get('success'):
                best_days = posting_patterns.get('best_days', [])
                best_hours = posting_patterns.get('best_hours', [])
                col_days, col_hours = st.columns(2)
                with col_days:
                    st.markdown("**Лучшие дни недели:**")
                    if best_days:
                        days_df = pd.DataFrame(best_days)
                        fig_days = px.bar(
                            days_df,
                            x='day',
                            y='avg_saves',
                            title='Avg Saves по дням недели',
                            labels={'day': 'День', 'avg_saves': 'Avg Saves'},
                            color='avg_saves',
                            color_continuous_scale='Blues'
                        )
                        st.plotly_chart(fig_days, use_container_width=True)
                with col_hours:
                    st.markdown("**Лучшие часы (MSK):**")
                    if best_hours:
                        hours_df = pd.DataFrame(best_hours)
                        fig_hours = px.bar(
                            hours_df,
                            x='hour',
                            y='avg_saves',
                            title='Avg Saves по часам (MSK)',
                            labels={'hour': 'Час', 'avg_saves': 'Avg Saves'},
                            color='avg_saves',
                            color_continuous_scale='Greens'
                        )
                        st.plotly_chart(fig_hours, use_container_width=True)
                st.success(f"✨ {posting_patterns.get('recommendation', '')}")
            else:
                st.info(posting_patterns.get('message', 'Недостаточно данных'))
        with analysis_tab5:
            st.markdown("### 💡 Инсайты для NIGINart")
            insights = analysis.get('insights_for_fashion_brand', {})
            if insights.get('success'):
                save_rate = insights.get('avg_save_rate', 0)
                benchmark = insights.get('save_rate_benchmark', 'unknown')
                benchmark_desc = insights.get('benchmark_description', '')
                benchmark_colors = {
                    'excellent': 'green',
                    'good': 'blue',
                    'poor': 'red'
                }
                col_metric1, col_metric2, col_metric3 = st.columns(3)
                with col_metric1:
                    st.metric(
                        "Avg Save Rate",
                        f"{save_rate:.2f}%",
                        help="Процент сохранений от охвата (покупательский интерес)"
                    )
                with col_metric2:
                    st.markdown(f"""
                    <div style="background-color: {benchmark_colors.get(benchmark, 'gray')};
                                color: white;
                                padding: 1rem;
                                border-radius: 0.5rem;
                                text-align: center;">
                        <h3 style="margin: 0;">{benchmark.upper()}</h3>
                        <p style="margin: 0;">{benchmark_desc}</p>
                    </div>
                    """, unsafe_allow_html=True)
                with col_metric3:
                    best_product = insights.get('best_performing_product', 'general')
                    st.metric(
                        "Лучшая категория",
                        best_product,
                        help="Категория товаров с наибольшим покупательским интересом"
                    )
                st.markdown("---")
                st.success(f"🎯 **Рекомендация:** {insights.get('recommendation', '')}")
                captions = analysis.get('captions', {})
                if captions.get('success'):
                    st.markdown("---")
                    st.markdown("**Анализ подписей и CTA:**")
                    col_cta1, col_cta2, col_cta3 = st.columns(3)
                    with col_cta1:
                        cta_count = captions.get('cta_posts_count', 0)
                        non_cta_count = captions.get('non_cta_posts_count', 0)
                        total = cta_count + non_cta_count
                        cta_pct = (cta_count / total * 100) if total > 0 else 0
                        st.metric("Посты с CTA", f"{cta_count} ({cta_pct:.0f}%)")
                    with col_cta2:
                        cta_avg_saves = captions.get('cta_avg_saves', 0)
                        st.metric("CTA: Avg Saves", cta_avg_saves)
                    with col_cta3:
                        non_cta_avg_saves = captions.get('non_cta_avg_saves', 0)
                        st.metric("Без CTA: Avg Saves", non_cta_avg_saves)
                    cta_effectiveness = captions.get('cta_effectiveness', 'insufficient_data')
                    effectiveness_messages = {
                        'higher': "✅ CTA посты приводят к большему количеству сохранений!",
                        'lower': "⚠️ Посты без CTA показывают лучшие результаты",
                        'similar': "ℹ️ CTA и обычные посты показывают похожие результаты",
                        'insufficient_data': "ℹ️ Недостаточно данных для оценки CTA"
                    }
                    st.info(effectiveness_messages.get(cta_effectiveness, ''))
            else:
                st.info(insights.get('message', 'Недостаточно данных'))
        current_followers = int(latest_df['followers'].sum()) if not latest_df.empty else 0
        _render_demographics(selected_account_id, current_followers)
st.markdown("---")
st.subheader("📋 Таблица метрик")
render_metrics_table(metrics_df)
with st.expander("🔍 Отладочная информация"):
    st.markdown("**Конфигурация:**")
    st.json({
        "platform": "instagram",
        "accounts_count": len(instagram_accounts),
        "selected_account": selected_account_id,
        "date_range": f"{start_date} - {end_date}",
        "data_points": data_points
    })
    st.markdown("**Последняя метрика (extra_data):**")
    if not latest_df.empty and 'extra_data' in latest_df.columns:
        st.json(latest_df.iloc[0]['extra_data'])
def _calculate_delta(current: float, previous: float) -> Optional[str]:
    if previous == 0:
        return None
    delta = current - previous
    if delta > 0:
        return f"+{delta:,}"
    elif delta < 0:
        return f"{delta:,}"
    return None
def _format_metric(value: float, format_type: str) -> str:
    if format_type == 'compact':
        return format_compact(value)
    elif format_type == 'number':
        return format_number(value)
    elif format_type == 'percent':
        return format_percent(value)
    return str(value)
def _render_media_card(post: Dict, index: int, expanded: bool = False) -> None:
    caption = post.get('caption', 'Без описания')
    caption_preview = caption[:60] + '...' if len(caption) > 60 else caption
    with st.expander(f"{index}. [{post.get('media_type')}] {caption_preview}", expanded=expanded):
        col1, col2 = st.columns([1, 2])
        with col1:
            permalink = post.get('permalink')
            if permalink:
                st.markdown(f"[🔗 Открыть в Instagram]({permalink})")
            st.write(f"**Тип:** {post.get('media_type', 'IMAGE')}")
        with col2:
            metrics_cols = st.columns(3)
            metrics_cols[0].metric("💾 Saves", post.get('saved', 0))
            metrics_cols[1].metric("👁️ Reach", format_compact(post.get('reach', 0)))
            metrics_cols[2].metric("📈 ER", f"{post.get('engagement_rate', 0):.1f}%")
            metrics_cols2 = st.columns(3)
            metrics_cols2[0].metric("❤️ Likes", post.get('likes', 0))
            metrics_cols2[1].metric("💬 Comments", post.get('comments', 0))
            metrics_cols2[2].metric("👀 Impressions", format_compact(post.get('impressions', 0)))
def _render_follower_growth_analysis(metrics_df, processor) -> None:
    daily_df = metrics_df.sort_values('collected_at')
    daily_df['follower_delta'] = daily_df['followers'].diff()
    growth_df = daily_df[daily_df['follower_delta'].notna()]
    if not growth_df.empty:
        avg_growth = growth_df['follower_delta'].mean()
        best_day = growth_df.loc[growth_df['follower_delta'].idxmax()]
        worst_day = growth_df.loc[growth_df['follower_delta'].idxmin()]
        positive_days_pct = (growth_df['follower_delta'] > 0).sum() / len(growth_df) * 100
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Среднее изменение", f"{avg_growth:+.0f}/день")
        col2.metric("Лучший день", f"{best_day['follower_delta']:+.0f}",
                   delta=best_day['collected_at'].strftime('%d.%m'))
        col3.metric("Худший день", f"{worst_day['follower_delta']:+.0f}",
                   delta=worst_day['collected_at'].strftime('%d.%m'))
        col4.metric("% дней роста", f"{positive_days_pct:.1f}%")
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=growth_df['collected_at'],
            y=growth_df['follower_delta'],
            mode='lines+markers',
            name='Прирост подписчиков',
            line=dict(color='#E1306C')
        ))
        fig.add_hline(y=0, line_dash="dash", line_color="gray")
        fig.update_layout(
            title="Ежедневный прирост подписчиков",
            xaxis_title="Дата",
            yaxis_title="Изменение",
            height=400
        )
        st.plotly_chart(fig, use_container_width=True)
def _render_demographics(account_id: UUID, followers_count: int) -> None:
    st.markdown("---")
    st.subheader("👥 Демография аудитории")
    if followers_count < 100:
        st.info("📊 Демографические данные доступны при 100+ подписчиков")
        return
    try:
        client = get_api_client()
        response = client.get(f"/api/v1/instagram/{account_id}/demographics")
        if response.status_code == 200:
            demographics = response.json()
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown("**Пол**")
                gender = demographics.get('gender_distribution', {})
                if gender:
                    fig = px.pie(
                        values=list(gender.values()),
                        names=list(gender.keys()),
                        color_discrete_map={'male': '#4A90D9', 'female': '#E91E63'}
                    )
                    fig.update_layout(showlegend=True, height=300)
                    st.plotly_chart(fig, use_container_width=True)
            with col2:
                st.markdown("**Возраст**")
                age_dist = demographics.get('age_distribution', {})
                if age_dist:
                    fig = px.bar(
                        x=list(age_dist.keys()),
                        y=list(age_dist.values()),
                        labels={'x': 'Возраст', 'y': 'Процент'}
                    )
                    fig.update_layout(height=300)
                    st.plotly_chart(fig, use_container_width=True)
            with col3:
                st.markdown("**Топ города**")
                cities = demographics.get('top_cities', [])
                if cities:
                    cities_df = pd.DataFrame(cities[:10])
                    fig = px.bar(
                        cities_df,
                        x='percentage',
                        y='city',
                        orientation='h',
                        labels={'percentage': '%', 'city': 'Город'}
                    )
                    fig.update_layout(height=300, yaxis={'categoryorder': 'total ascending'})
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("⚠️ Не удалось загрузить демографические данные")
    except Exception as e:
        st.warning(f"⚠️ Демография недоступна: {e}")
