import streamlit as st
import pandas as pd
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
from dashboard.components.account_manager import render_account_card
from dashboard.components.video_table import render_video_table
from dashboard.components.top_videos import render_top_video_card
from dashboard.services.cache_manager import (
    fetch_accounts_cached,
    fetch_metrics_cached,
    clear_all_caches
)
from dashboard.services.data_processor import MetricsProcessor
from dashboard.services.api_client import get_api_client
def safe_int(value, default=0):
    try:
        if pd.isna(value):
            return default
        return int(value)
    except (ValueError, TypeError):
        return default
st.set_page_config(
    page_title=f"YouTube - {PAGE_TITLE}",
    page_icon="📺",
    layout="wide"
)
init_session_state()
st.title("📺 YouTube Analytics")
st.markdown("Аналитика YouTube каналов")
st.markdown("---")
col1, col2, col3 = st.columns([2, 2, 1])
with col1:
    try:
        youtube_accounts = fetch_accounts_cached(platform='youtube')
    except Exception as e:
        st.error(f"⚠️ Ошибка загрузки аккаунтов: {e}")
        st.stop()
    if not youtube_accounts:
        st.warning("⚠️ Нет аккаунтов YouTube")
        st.markdown("""
        **Действия:**
        - Добавьте YouTube аккаунты через API
        - Запустите сбор данных
        """)
        st.stop()
    selected_account_id = render_account_filter(youtube_accounts)
with col2:
    start_date, end_date = render_date_range_filter()
with col3:
    st.write("Период метрик")
    selected_period = st.radio(
        "период",
        options=['7d', '30d', '90d'],
        index=1,
        horizontal=True,
        key='youtube_period_selector',
        label_visibility='collapsed'
    )
    st.caption("ℹ️ За какой срок считать метрики видео")
try:
    with st.spinner("Загрузка метрик..."):
        metrics_df = fetch_metrics_cached(
            platform='youtube',
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
data_points = len(metrics_df)
if data_points == 1:
    st.warning("⚠️ Собрана только 1 точка данных. Для визуализации трендов запустите сбор несколько раз или включите автоматический сбор.")
elif data_points < 5:
    st.info(f"📊 Собрано {data_points} точек данных. Рекомендуется минимум 5 для анализа трендов.")
def get_period_metric(df: pd.DataFrame, period: str, metric: str, default=None):
    column_name = f'metrics_{period}.{metric}'
    return df[column_name] if column_name in df.columns else default
def calculate_pct_change(current: float, previous: float) -> Optional[float]:
    if previous is None or previous == 0:
        return None
    return ((current - previous) / abs(previous)) * 100
processor = MetricsProcessor()
latest_df = processor.aggregate_by_account(metrics_df)
current_subscribers = safe_int(latest_df['followers'].sum())
current_videos = safe_int(latest_df['posts_count'].sum())
engagement_series = get_period_metric(latest_df, selected_period, 'engagement_rate')
current_engagement = float(engagement_series.mean()) if engagement_series is not None else 0.0
current_avg_likes = 0
if selected_period == '30d':
    avg_likes_series = get_period_metric(latest_df, '30d', 'avg_likes_per_video')
    if avg_likes_series is not None:
        current_avg_likes = float(avg_likes_series.mean())
avg_views_series = get_period_metric(latest_df, selected_period, 'avg_views_per_video')
current_avg_views = float(avg_views_series.mean()) if avg_views_series is not None else 0.0
total_views_series = get_period_metric(latest_df, selected_period, 'total_views')
current_total_views = safe_int(total_views_series.sum()) if total_views_series is not None else 0
period_length = (end_date - start_date).days
if period_length > 0:
    prev_start = start_date - timedelta(days=period_length)
    prev_end = start_date
    try:
        prev_metrics_df = fetch_metrics_cached(
            platform='youtube',
            start_date=prev_start,
            end_date=prev_end,
            account_id=None if selected_account_id == 'all' else selected_account_id
        )
        if not prev_metrics_df.empty:
            prev_latest = processor.aggregate_by_account(prev_metrics_df)
            prev_subscribers = safe_int(prev_latest['followers'].sum())
            prev_videos = safe_int(prev_latest['posts_count'].sum())
            prev_eng_series = get_period_metric(prev_latest, selected_period, 'engagement_rate')
            prev_engagement = float(prev_eng_series.mean()) if prev_eng_series is not None else 0.0
            if selected_period == '30d':
                prev_likes_series = get_period_metric(prev_latest, '30d', 'avg_likes_per_video')
                prev_avg_likes = float(prev_likes_series.mean()) if prev_likes_series is not None else 0
            else:
                prev_avg_likes = 0
            prev_avg_views_series = get_period_metric(prev_latest, selected_period, 'avg_views_per_video')
            prev_avg_views = float(prev_avg_views_series.mean()) if prev_avg_views_series is not None else 0.0
            prev_total_views_series = get_period_metric(prev_latest, selected_period, 'total_views')
            prev_total_views = safe_int(prev_total_views_series.sum()) if prev_total_views_series is not None else 0
            delta_subscribers = current_subscribers - prev_subscribers
            delta_videos = current_videos - prev_videos
            delta_engagement = current_engagement - prev_engagement
            delta_avg_likes = current_avg_likes - prev_avg_likes
            delta_avg_views = current_avg_views - prev_avg_views
            delta_total_views = current_total_views - prev_total_views
        else:
            delta_subscribers = delta_videos = delta_engagement = delta_avg_likes = delta_avg_views = delta_total_views = None
    except:
        delta_subscribers = delta_videos = delta_engagement = delta_avg_likes = delta_avg_views = delta_total_views = None
else:
    delta_subscribers = delta_videos = delta_engagement = delta_avg_likes = delta_avg_views = delta_total_views = None
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
col1, col2, col3, col4, col5, col6 = st.columns(6)
with col1:
    render_kpi_card(
        "Подписчики",
        current_subscribers,
        delta=delta_subscribers,
        format_type='compact'
    )
with col2:
    if selected_period == '30d':
        render_kpi_card(
            "Средние лайки (30д)",
            current_avg_likes,
            delta=delta_avg_likes,
            format_type='compact'
        )
    else:
        st.metric(
            label=f"Средние лайки ({selected_period})",
            value="—",
            help="Доступно только для 30 дней"
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
        f"Вовлеченность ({selected_period})",
        current_engagement,
        delta=delta_engagement,
        format_type='percent'
    )
with col5:
    render_kpi_card(
        f"Средн. просмотры ({selected_period})",
        current_avg_views,
        delta=delta_avg_views,
        format_type='compact'
    )
with col6:
    render_kpi_card(
        f"Всего просмотров ({selected_period})",
        current_total_views,
        delta=delta_total_views,
        format_type='compact'
    )
st.markdown("---")
with st.expander("📊 Сравнение с предыдущим периодом", expanded=False):
    if delta_subscribers is not None:
        pct_subscribers = calculate_pct_change(current_subscribers, current_subscribers - delta_subscribers if delta_subscribers else 0)
        pct_videos = calculate_pct_change(current_videos, current_videos - delta_videos if delta_videos else 0)
        pct_engagement = calculate_pct_change(current_engagement, current_engagement - delta_engagement if delta_engagement else 0)
        pct_avg_likes = calculate_pct_change(current_avg_likes, current_avg_likes - delta_avg_likes if delta_avg_likes else 0) if selected_period == '30d' else None
        pct_avg_views = calculate_pct_change(current_avg_views, current_avg_views - delta_avg_views if delta_avg_views else 0)
        pct_total_views = calculate_pct_change(current_total_views, current_total_views - delta_total_views if delta_total_views else 0)
        comparison_data = []
        comparison_data.append({
            "Метрика": "Подписчики",
            "Текущее": format_compact(current_subscribers),
            "Изменение": f"+{format_compact(delta_subscribers)}" if delta_subscribers > 0 else format_compact(delta_subscribers),
            "% Изменение": f"{pct_subscribers:+.1f}%" if pct_subscribers is not None else "—"
        })
        if selected_period == '30d':
            comparison_data.append({
                "Метрика": "Средние лайки (30д)",
                "Текущее": format_compact(current_avg_likes),
                "Изменение": f"+{format_compact(delta_avg_likes)}" if delta_avg_likes > 0 else format_compact(delta_avg_likes),
                "% Изменение": f"{pct_avg_likes:+.1f}%" if pct_avg_likes is not None else "—"
            })
        else:
            comparison_data.append({
                "Метрика": f"Средние лайки ({selected_period})",
                "Текущее": "—",
                "Изменение": "—",
                "% Изменение": "Недоступно для этого периода"
            })
        comparison_data.append({
            "Метрика": "Всего видео",
            "Текущее": format_number(current_videos),
            "Изменение": f"+{format_number(delta_videos)}" if delta_videos > 0 else format_number(delta_videos),
            "% Изменение": f"{pct_videos:+.1f}%" if pct_videos is not None else "—"
        })
        comparison_data.append({
            "Метрика": f"Вовлеченность ({selected_period})",
            "Текущее": format_percent(current_engagement),
            "Изменение": f"+{format_percent(delta_engagement)}" if delta_engagement > 0 else format_percent(delta_engagement),
            "% Изменение": f"{pct_engagement:+.1f}%" if pct_engagement is not None else "—"
        })
        comparison_data.append({
            "Метрика": f"Средн. просмотры ({selected_period})",
            "Текущее": format_compact(current_avg_views),
            "Изменение": f"+{format_compact(delta_avg_views)}" if delta_avg_views > 0 else format_compact(delta_avg_views),
            "% Изменение": f"{pct_avg_views:+.1f}%" if pct_avg_views is not None else "—"
        })
        comparison_data.append({
            "Метрика": f"Всего просмотров ({selected_period})",
            "Текущее": format_compact(current_total_views),
            "Изменение": f"+{format_compact(delta_total_views)}" if delta_total_views > 0 else format_compact(delta_total_views),
            "% Изменение": f"{pct_total_views:+.1f}%" if pct_total_views is not None else "—"
        })
        st.table(comparison_data)
    else:
        st.info("Недостаточно данных для сравнения с предыдущим периодом")
st.markdown("---")
tab1, tab2, tab3 = st.tabs(["📈 Динамика", "📊 Обзор аккаунтов", "⚙️ Аккаунты"])
with tab1:
    st.subheader("Динамика показателей")
    if len(metrics_df) == 0:
        st.warning("📊 Нет данных для отображения. Запустите сбор метрик через вкладку 'Управление аккаунтами' или API.")
    else:
        subscribers_ts = processor.prepare_time_series(metrics_df, 'followers', resample_freq='D')
        if not subscribers_ts.empty:
            chart = ChartBuilder.line_chart(
                subscribers_ts,
                x='collected_at',
                y='followers',
                title='Динамика подписчиков',
                y_label='Подписчики',
                color=PLATFORM_COLORS['youtube']
            )
            st.plotly_chart(chart, use_container_width=True)
        st.subheader("📊 Прирост подписчиков")
        growth_df = processor.calculate_growth(metrics_df, 'followers')
        if 'followers_change' not in growth_df.columns or growth_df['followers_change'].isna().all():
            st.info("Недостаточно данных для расчета прироста подписчиков. Требуется минимум 2 точки данных.")
        else:
            valid_growth = growth_df['followers_change'].dropna()
            if valid_growth.empty:
                st.info("Нет доступных данных о приросте подписчиков.")
            else:
                avg_growth = valid_growth.mean()
                max_growth = valid_growth.max()
                min_growth = valid_growth.min()
                positive_days_pct = (valid_growth > 0).sum() / len(valid_growth) * 100 if len(valid_growth) > 0 else 0
                best_day_date = growth_df.loc[growth_df['followers_change'] == max_growth, 'collected_at'].iloc[0] if max_growth in valid_growth.values else None
                worst_day_date = growth_df.loc[growth_df['followers_change'] == min_growth, 'collected_at'].iloc[0] if min_growth in valid_growth.values else None
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric(
                        label="Средний прирост",
                        value=format_number(avg_growth),
                        delta=None
                    )
                with col2:
                    st.metric(
                        label="Лучший день",
                        value=format_number(max_growth),
                        delta=best_day_date.strftime('%d.%m.%Y') if best_day_date else None
                    )
                with col3:
                    st.metric(
                        label="Худший день",
                        value=format_number(min_growth),
                        delta=worst_day_date.strftime('%d.%m.%Y') if worst_day_date else None
                    )
                with col4:
                    st.metric(
                        label="Дней с ростом",
                        value=f"{positive_days_pct:.1f}%",
                        delta=None
                    )
                growth_ts = processor.prepare_time_series(growth_df, 'followers_change', resample_freq='D')
                if not growth_ts.empty:
                    chart = ChartBuilder.line_chart(
                        growth_ts,
                        x='collected_at',
                        y='followers_change',
                        title='Ежедневный прирост подписчиков',
                        y_label='Изменение подписчиков',
                        color=PLATFORM_COLORS['youtube']
                    )
                    chart.add_hline(
                        y=0,
                        line_dash="dash",
                        line_color="gray",
                        opacity=0.5,
                        annotation_text="",
                        annotation_position="right"
                    )
                    st.plotly_chart(chart, use_container_width=True)
                else:
                    st.info("Нет данных для отображения графика прироста.")
        if 'engagement_rate' in metrics_df.columns:
            er_ts = processor.prepare_time_series(metrics_df, 'engagement_rate', resample_freq='D')
            if not er_ts.empty:
                chart = ChartBuilder.line_chart(
                    er_ts,
                    x='collected_at',
                    y='engagement_rate',
                    title='Динамика вовлеченности',
                    y_label='ER %',
                    color=PLATFORM_COLORS['youtube']
                )
                st.plotly_chart(chart, use_container_width=True)
        METRIC_CONFIG = {
            "Средние лайки на видео": {
                "key": "avg_likes_per_video",
                "periods": ["30d"],
                "y_label": "Лайки",
                "title": "Динамика средних лайков на видео",
                "format": "compact",
                "description": "Среднее количество лайков на видео"
            },
            "Средние комментарии на видео": {
                "key": "avg_comments_per_video",
                "periods": ["30d"],
                "y_label": "Комментарии",
                "title": "Динамика средних комментариев на видео",
                "format": "compact",
                "description": "Среднее количество комментариев на видео"
            },
            "Средние просмотры на видео": {
                "key": "avg_views_per_video",
                "periods": ["7d", "30d", "90d"],
                "y_label": "Просмотры",
                "title": "Динамика средних просмотров на видео",
                "format": "compact",
                "description": "Среднее количество просмотров на видео"
            },
            "Engagement Rate": {
                "key": "engagement_rate",
                "periods": ["7d", "30d", "90d"],
                "y_label": "ER %",
                "title": "Динамика вовлеченности",
                "format": "percent",
                "description": "Процент вовлеченности аудитории"
            }
        }
        st.subheader("📊 Динамика метрик видео")
        selected_metric_label = st.selectbox(
            "Выберите метрику для анализа",
            options=list(METRIC_CONFIG.keys()),
            index=0,
            key='youtube_metric_selector'
        )
        metric_cfg = METRIC_CONFIG[selected_metric_label]
        metric_key = metric_cfg['key']
        available_periods = metric_cfg['periods']
        column_name = f'metrics_{selected_period}.{metric_key}'
        is_available = selected_period in available_periods
        if not is_available:
            st.warning(
                f"⚠️ **{selected_metric_label}** доступны только для периода **30 дней**.\n\n"
                f"Вы выбрали период: **{selected_period}**. "
                f"Измените период на 30d или выберите другую метрику (Engagement Rate или Средние просмотры)."
            )
            st.caption(
                f"ℹ️ Метрика '{metric_cfg['description']}' собирается только за 30-дневный период "
                f"из-за ограничений YouTube Data API."
            )
        elif column_name not in metrics_df.columns:
            st.info(
                f"📊 Данные для метрики **{selected_metric_label}** пока не собраны.\n\n"
                f"Запустите сбор метрик через вкладку 'Управление аккаунтами' или API."
            )
        else:
            metric_ts = processor.prepare_time_series(metrics_df, column_name, resample_freq='D')
            if metric_ts.empty or metric_ts[column_name].isna().all():
                st.info(
                    f"📊 Нет данных для метрики **{selected_metric_label}** за выбранный период.\n\n"
                    f"Данные могут отсутствовать, если сбор не производился или все значения пустые."
                )
            else:
                valid_values = metric_ts[column_name].dropna()
                current_value = valid_values.iloc[-1] if len(valid_values) > 0 else 0
                avg_value = valid_values.mean()
                max_value = valid_values.max()
                col1, col2, col3 = st.columns(3)
                with col1:
                    render_kpi_card(
                        "Текущее значение",
                        current_value,
                        delta=None,
                        format_type=metric_cfg['format']
                    )
                with col2:
                    render_kpi_card(
                        "Среднее",
                        avg_value,
                        delta=None,
                        format_type=metric_cfg['format']
                    )
                with col3:
                    render_kpi_card(
                        "Максимум",
                        max_value,
                        delta=None,
                        format_type=metric_cfg['format']
                    )
                chart = ChartBuilder.line_chart(
                    metric_ts,
                    x='collected_at',
                    y=column_name,
                    title=metric_cfg['title'],
                    y_label=metric_cfg['y_label'],
                    color=PLATFORM_COLORS['youtube']
                )
                chart.add_hline(
                    y=avg_value,
                    line_dash="dash",
                    line_color="rgba(255, 99, 71, 0.6)",
                    opacity=0.7,
                    annotation_text=f"Среднее: {format_compact(avg_value) if metric_cfg['format'] == 'compact' else format_percent(avg_value)}",
                    annotation_position="right"
                )
                st.plotly_chart(chart, use_container_width=True)
                period_labels = {'7d': '7 дней', '30d': '30 дней', '90d': '90 дней'}
                st.caption(
                    f"📊 Источник: {metric_cfg['description']} за период {period_labels[selected_period]} | "
                    f"Точек данных: {len(valid_values)} | "
                    f"Последнее обновление: {metric_ts['collected_at'].max().strftime('%d.%m.%Y %H:%M')}"
                )
        period_labels = {'7d': '7 дней', '30d': '30 дней', '90d': '90 дней'}
        views_column = f'metrics_{selected_period}.total_views'
        if views_column in metrics_df.columns:
            views_ts = processor.prepare_time_series(metrics_df, views_column, resample_freq='D')
            if not views_ts.empty:
                chart = ChartBuilder.line_chart(
                    views_ts,
                    x='collected_at',
                    y=views_column,
                    title=f'Динамика просмотров ({period_labels[selected_period]})',
                    y_label='Просмотры',
                    color=PLATFORM_COLORS['youtube']
                )
                st.plotly_chart(chart, use_container_width=True)
        st.markdown("---")
        if not latest_df.empty:
            if selected_account_id != 'all':
                account_row = latest_df[latest_df.index == selected_account_id]
            else:
                account_row = latest_df.iloc[[0]]
            if not account_row.empty and 'recent_videos' in account_row.columns:
                recent_videos = account_row.iloc[0]['recent_videos']
                if isinstance(recent_videos, list) and len(recent_videos) > 0:
                    render_video_table(recent_videos, title="Последние видео (30 дней)")
                else:
                    st.info("📹 Нет данных о последних видео. Запустите сбор метрик.")
        st.markdown("---")
        st.subheader("🏆 Топ видео")
        if not latest_df.empty:
            if selected_account_id != 'all':
                account_row = latest_df[latest_df.index == selected_account_id]
            else:
                account_row = latest_df.iloc[[0]]
            if not account_row.empty and 'recent_videos' in account_row.columns:
                recent_videos = account_row.iloc[0]['recent_videos']
                if isinstance(recent_videos, list) and len(recent_videos) > 0:
                    col_filter1, col_filter2 = st.columns(2)
                    with col_filter1:
                        sort_options = {
                            "Просмотрам": "views",
                            "Лайкам": "likes",
                            "Комментариям": "comments",
                            "Дате публикации": "published_at"
                        }
                        selected_sort_label = st.selectbox(
                            "Сортировать по",
                            options=list(sort_options.keys()),
                            index=0,
                            key='top_videos_sort'
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
                            key='top_videos_count'
                        )
                    data = []
                    for video in recent_videos:
                        views = video.get('views', 0)
                        likes = video.get('likes', 0)
                        comments = video.get('comments', 0)
                        engagement_rate = ((likes + comments) / max(views, 1) * 100)
                        published_at_str = video.get('published_at', '')
                        published_dt = None
                        if published_at_str:
                            try:
                                published_dt = datetime.fromisoformat(published_at_str.replace('Z', '+00:00'))
                            except (ValueError, AttributeError):
                                published_dt = None
                        date_display = published_dt.strftime('%d.%m.%Y') if published_dt else 'N/A'
                        video_id = video.get('video_id', '')
                        video_url = f"https://youtube.com/watch?v={video_id}"
                        data.append({
                            'Название': video.get('title', 'Без названия'),
                            'URL': video_url,
                            'Дата': date_display,
                            'published_dt': published_dt,
                            'Просмотры': views,
                            'Лайки': likes,
                            'Комментарии': comments,
                            'ER %': engagement_rate,
                            'video_id': video_id
                        })
                    videos_df = pd.DataFrame(data)
                    sort_field_mapping = {
                        'views': 'Просмотры',
                        'likes': 'Лайки',
                        'comments': 'Комментарии',
                        'published_at': 'published_dt'
                    }
                    if sort_field == 'published_at':
                        videos_df = videos_df.sort_values('published_dt', ascending=False, na_position='last')
                    else:
                        actual_sort_field = sort_field_mapping.get(sort_field, sort_field)
                        videos_df = videos_df.sort_values(actual_sort_field, ascending=False)
                    top_videos_df = videos_df.head(video_count)
                    display_df = top_videos_df.drop(columns=['published_dt', 'video_id'])
                    st.dataframe(
                        display_df,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            'Название': st.column_config.TextColumn('Название', width='large'),
                            'URL': st.column_config.LinkColumn('Ссылка', display_text='YouTube'),
                            'Дата': st.column_config.TextColumn('Дата', width='small'),
                            'Просмотры': st.column_config.NumberColumn('Просмотры', format='%d'),
                            'Лайки': st.column_config.NumberColumn('Лайки', format='%d'),
                            'Комментарии': st.column_config.NumberColumn('Комментарии', format='%d'),
                            'ER %': st.column_config.NumberColumn('ER %', format='%.2f'),
                        }
                    )
                    total_views = safe_int(top_videos_df['Просмотры'].sum())
                    avg_views = safe_int(top_videos_df['Просмотры'].mean())
                    avg_er = float(top_videos_df['ER %'].mean()) if not pd.isna(top_videos_df['ER %'].mean()) else 0.0
                    st.markdown("#### Статистика выбранных видео")
                    stat_col1, stat_col2, stat_col3 = st.columns(3)
                    with stat_col1:
                        st.metric("Всего просмотров", format_compact(total_views))
                    with stat_col2:
                        st.metric("Средние просмотры", format_compact(avg_views))
                    with stat_col3:
                        st.metric("Средний ER", format_percent(avg_er))
                    st.markdown("---")
                    st.markdown("#### Открыть видео")
                    video_options = {}
                    for idx, row in top_videos_df.iterrows():
                        title = row['Название']
                        display_title = title[:50] + "..." if len(title) > 50 else title
                        video_options[display_title] = row['video_id']
                    if video_options:
                        opener_col1, opener_col2 = st.columns([3, 1])
                        with opener_col1:
                            selected_video_title = st.selectbox(
                                "Выберите видео",
                                options=list(video_options.keys()),
                                key='video_opener_select'
                            )
                        with opener_col2:
                            selected_video_id = video_options[selected_video_title]
                            video_url = f"https://youtube.com/watch?v={selected_video_id}"
                            st.markdown("<br>", unsafe_allow_html=True)
                            st.link_button("🎥 Открыть видео", url=video_url, use_container_width=True)
                else:
                    st.info("📹 Нет данных о последних видео. Запустите сбор метрик.")
            else:
                st.info("📹 Нет данных о последних видео. Запустите сбор метрик.")
with tab2:
    st.subheader("Обзор аккаунтов")
    if selected_account_id == 'all':
        if len(latest_df) > 1:
            latest_sorted = latest_df.sort_values('followers', ascending=True)
            chart = ChartBuilder.bar_chart(
                latest_sorted,
                x='followers',
                y='display_name' if 'display_name' in latest_sorted.columns else 'account_id',
                title='Подписчики по аккаунтам',
                x_label='Подписчики',
                y_label='Аккаунт',
                color=PLATFORM_COLORS['youtube']
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
                    color=PLATFORM_COLORS['youtube']
                )
                st.plotly_chart(chart, use_container_width=True)
            if selected_period == '30d':
                column_name = 'metrics_30d.avg_likes_per_video'
                if column_name in latest_df.columns:
                    likes_sorted = latest_df.sort_values(column_name, ascending=True)
                    chart = ChartBuilder.bar_chart(
                        likes_sorted,
                        x=column_name,
                        y='display_name' if 'display_name' in likes_sorted.columns else 'account_id',
                        title='Средние лайки по аккаунтам (30 дней)',
                        x_label='Лайки на видео',
                        y_label='Аккаунт',
                        color=PLATFORM_COLORS['youtube']
                    )
                    st.plotly_chart(chart, use_container_width=True)
            else:
                st.info(f"📊 Сравнение средних лайков доступно только для периода 30 дней")
        else:
            st.info("У вас один YouTube аккаунт. Данные отображаются в таблице ниже.")
            account = latest_df.iloc[0]
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Подписчики", f"{safe_int(account['followers']):,}")
            with col2:
                eng_column = f'metrics_{selected_period}.engagement_rate'
                if eng_column in account.index and pd.notna(account[eng_column]):
                    st.metric(f"Вовлеченность ({selected_period})", f"{account[eng_column]:.2f}%")
            with col3:
                if selected_period == '30d':
                    likes_column = 'metrics_30d.avg_likes_per_video'
                    if likes_column in account.index and pd.notna(account[likes_column]):
                        st.metric("Средние лайки (30д)", f"{account[likes_column]:.1f}")
                else:
                    st.metric("Средние лайки", "—", help="Доступно только для 30д")
            with col4:
                st.metric("Всего видео", f"{safe_int(account['posts_count']):,}")
    else:
        selected_account = latest_df[latest_df.index == selected_account_id]
        if not selected_account.empty:
            account = selected_account.iloc[0]
            account_name = account.get('display_name', account.get('account_id', 'Unknown'))
            st.info(f"📊 Аккаунт: **{account_name}**")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Подписчики", f"{safe_int(account['followers']):,}")
            with col2:
                eng_column = f'metrics_{selected_period}.engagement_rate'
                if eng_column in account.index and pd.notna(account[eng_column]):
                    st.metric(f"Вовлеченность ({selected_period})", f"{account[eng_column]:.2f}%")
            with col3:
                if selected_period == '30d':
                    likes_column = 'metrics_30d.avg_likes_per_video'
                    if likes_column in account.index and pd.notna(account[likes_column]):
                        st.metric("Средние лайки (30д)", f"{account[likes_column]:.1f}")
                else:
                    st.metric("Средние лайки", "—", help="Доступно только для 30д")
            with col4:
                st.metric("Всего видео", f"{safe_int(account['posts_count']):,}")
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
    if youtube_accounts:
        for account in youtube_accounts:
            render_account_card(account, on_toggle=toggle_account_status)
    else:
        st.info("Нет аккаунтов для отображения")
st.markdown("---")
st.caption(f"Последнее обновление: {datetime.now().strftime('%d.%m.%Y %H:%M')}")
