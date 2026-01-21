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
st.set_page_config(
    page_title=f"Pinterest - {PAGE_TITLE}",
    page_icon="📌",
    layout="wide"
)
init_session_state()
st.title("📌 Pinterest Analytics")
st.markdown("Аналитика Pinterest аккаунтов через Pinterest API v5")
query_params = st.query_params
if "oauth_success" in query_params and query_params["oauth_success"] == "true":
    st.success("✅ Pinterest аккаунт успешно подключен!")
    st.balloons()
    st.query_params.clear()
if "oauth_error" in query_params:
    error_type = query_params["oauth_error"]
    error_messages = {
        "invalid_state": "❌ Ошибка безопасности: недействительный CSRF токен.",
        "pinterest_api_error": "❌ Ошибка Pinterest API. Проверьте учетные данные.",
        "invalid_response": "❌ Неверный формат ответа от Pinterest.",
        "unknown": "❌ Неизвестная ошибка при авторизации."
    }
    st.error(error_messages.get(error_type, f"❌ Ошибка OAuth: {error_type}"))
    st.query_params.clear()
st.markdown("---")
col1, col2 = st.columns([2, 2])
with col1:
    try:
        pinterest_accounts = fetch_accounts_cached(platform='pinterest')
    except Exception as e:
        st.error(f"⚠️ Ошибка загрузки аккаунтов: {e}")
        st.stop()
    if not pinterest_accounts:
        st.warning("⚠️ Нет подключенных Pinterest аккаунтов")
        col_a, col_b = st.columns([1, 2])
        with col_a:
            if st.button("🔗 Подключить Pinterest", type="primary", use_container_width=True):
                try:
                    client = get_api_client()
                    response = client.get("/api/v1/oauth/pinterest/start")
                    if response.status_code == 200:
                        data = response.json()
                        auth_url = data.get("authorization_url")
                        st.markdown(f"""
                        <a href="{auth_url}" target="_blank" style="
                            display: inline-block;
                            padding: 0.5rem 1rem;
                            background-color: #bd081c;
                            color: white;
                            text-decoration: none;
                            border-radius: 0.25rem;
                            font-weight: 600;
                        ">📌 Авторизовать Pinterest</a>
                        """, unsafe_allow_html=True)
                    else:
                        st.error(f"⚠️ Ошибка: {response.text}")
                except Exception as e:
                    st.error(f"⚠️ Ошибка подключения: {e}")
        with col_b:
            st.info("""
            **Подключите аккаунт для просмотра:**
            - Динамика подписчиков
            - Статистика пинов
            - Аналитика сохранений
            - Топ пинов по эффективности
            """)
        st.stop()
    selected_account_id = render_account_filter(pinterest_accounts)
with col2:
    start_date, end_date = render_date_range_filter()
try:
    with st.spinner("Загрузка метрик..."):
        metrics_df = fetch_metrics_cached(
            platform='pinterest',
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
current_pins = int(latest_df['posts_count'].sum())
current_monthly_views = int(latest_df['total_views'].sum())
current_engagement = float(latest_df['engagement_rate'].mean())
current_saves_30d = 0
if 'extra_data' in latest_df.columns:
    for _, row in latest_df.iterrows():
        extra = row.get('extra_data')
        if isinstance(extra, dict):
            current_saves_30d += extra.get('saves_30d', 0)
period_length = (end_date - start_date).days
if period_length > 0:
    prev_start = start_date - timedelta(days=period_length)
    prev_end = start_date
    try:
        prev_metrics_df = fetch_metrics_cached(
            platform='pinterest',
            start_date=prev_start,
            end_date=prev_end,
            account_id=None if selected_account_id == 'all' else selected_account_id
        )
        if not prev_metrics_df.empty:
            prev_latest = processor.aggregate_by_account(prev_metrics_df)
            prev_followers = int(prev_latest['followers'].sum())
            prev_pins = int(prev_latest['posts_count'].sum())
            prev_monthly_views = int(prev_latest['total_views'].sum())
            prev_engagement = float(prev_latest['engagement_rate'].mean())
            delta_followers = current_followers - prev_followers
            delta_pins = current_pins - prev_pins
            delta_views = current_monthly_views - prev_monthly_views
            delta_engagement = current_engagement - prev_engagement
        else:
            delta_followers = delta_pins = delta_views = delta_engagement = None
    except:
        delta_followers = delta_pins = delta_views = delta_engagement = None
else:
    delta_followers = delta_pins = delta_views = delta_engagement = None
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
        "Всего пинов",
        current_pins,
        delta=delta_pins,
        format_type='number'
    )
with col4:
    render_kpi_card(
        "Просмотры/мес",
        current_monthly_views,
        delta=delta_views,
        format_type='compact'
    )
st.markdown("---")
tab1, tab2, tab3 = st.tabs([
    "📈 Динамика",
    "📌 Топ пинов",
    "📊 Аналитика 30д"
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
                color=PLATFORM_COLORS.get('pinterest', '#bd081c')
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
                        color=PLATFORM_COLORS.get('pinterest', '#bd081c')
                    )
                    chart.add_hline(
                        y=0,
                        line_dash="dash",
                        line_color="gray",
                        opacity=0.5
                    )
                    st.plotly_chart(chart, use_container_width=True)
        if 'total_views' in metrics_df.columns:
            views_ts = processor.prepare_time_series(metrics_df, 'total_views', resample_freq='D')
            if not views_ts.empty:
                chart = ChartBuilder.line_chart(
                    views_ts,
                    x='collected_at',
                    y='total_views',
                    title='Динамика просмотров профиля',
                    y_label='Просмотры/месяц',
                    color=PLATFORM_COLORS.get('pinterest', '#bd081c')
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
                    color=PLATFORM_COLORS.get('pinterest', '#bd081c')
                )
                st.plotly_chart(chart, use_container_width=True)
with tab2:
    st.subheader("📌 Топ пинов")
    top_pins_data = []
    if not latest_df.empty and 'extra_data' in latest_df.columns:
        if selected_account_id != 'all':
            account_row = latest_df[latest_df.index == selected_account_id]
        else:
            account_row = latest_df.iloc[[0]]
        if not account_row.empty:
            extra_data = account_row.iloc[0].get('extra_data')
            if isinstance(extra_data, dict):
                top_pins_data = extra_data.get('top_pins', [])
    if top_pins_data:
        col_filter1, col_filter2 = st.columns(2)
        with col_filter1:
            sort_options = {
                "Показам": "impressions",
                "Сохранениям": "saves",
                "Кликам на пин": "pin_clicks",
                "Переходам": "outbound_clicks"
            }
            selected_sort_label = st.selectbox(
                "Сортировать по",
                options=list(sort_options.keys()),
                index=0,
                key='pinterest_pins_sort'
            )
            sort_field = sort_options[selected_sort_label]
        with col_filter2:
            max_pins = len(top_pins_data)
            default_count = min(10, max_pins)
            pin_count = st.number_input(
                "Количество пинов",
                min_value=1,
                max_value=max_pins,
                value=default_count,
                step=1,
                key='pinterest_pins_count'
            )
        pins_df = pd.DataFrame(top_pins_data)
        if not pins_df.empty:
            pins_df = pins_df.sort_values(sort_field, ascending=False)
            top_pins = pins_df.head(pin_count)
            for i, pin in enumerate(top_pins.to_dict('records'), 1):
                pin_id = pin.get('pin_id', 'Unknown')
                impressions = pin.get('impressions', 0)
                saves = pin.get('saves', 0)
                pin_clicks = pin.get('pin_clicks', 0)
                outbound_clicks = pin.get('outbound_clicks', 0)
                with st.expander(f"{i}. Pin ID: {pin_id[:20]}...", expanded=(i <= 3)):
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("👁 Показы", format_compact(impressions))
                    with col2:
                        st.metric("💾 Сохранения", format_compact(saves))
                    with col3:
                        st.metric("👆 Клики на пин", format_compact(pin_clicks))
                    with col4:
                        st.metric("🔗 Переходы", format_compact(outbound_clicks))
                    if impressions > 0:
                        save_rate = (saves / impressions) * 100
                        click_rate = (pin_clicks / impressions) * 100
                        st.caption(f"Save Rate: {save_rate:.2f}% | Click Rate: {click_rate:.2f}%")
                    st.markdown(f"[📌 Открыть на Pinterest](https://pinterest.com/pin/{pin_id})")
            st.markdown("---")
            st.markdown("#### Статистика выбранных пинов")
            stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)
            with stat_col1:
                st.metric("Всего показов", format_compact(int(top_pins['impressions'].sum())))
            with stat_col2:
                st.metric("Всего сохранений", format_compact(int(top_pins['saves'].sum())))
            with stat_col3:
                st.metric("Средние показы", format_compact(int(top_pins['impressions'].mean())))
            with stat_col4:
                avg_save_rate = (top_pins['saves'].sum() / max(top_pins['impressions'].sum(), 1)) * 100
                st.metric("Средний Save Rate", f"{avg_save_rate:.2f}%")
    else:
        st.info("📌 Нет данных о топ пинах. Запустите сбор метрик для получения данных.")
with tab3:
    st.subheader("📊 Аналитика за 30 дней")
    analytics_data = None
    if not latest_df.empty and 'extra_data' in latest_df.columns:
        if selected_account_id != 'all':
            account_row = latest_df[latest_df.index == selected_account_id]
        else:
            account_row = latest_df.iloc[[0]]
        if not account_row.empty:
            extra_data = account_row.iloc[0].get('extra_data')
            if isinstance(extra_data, dict):
                analytics_data = extra_data
    if analytics_data:
        st.markdown("### Ключевые метрики (30 дней)")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Показы", format_compact(analytics_data.get('impressions_30d', 0)))
        with col2:
            st.metric("Вовлечения", format_compact(analytics_data.get('engagements_30d', 0)))
        with col3:
            st.metric("Сохранения", format_compact(analytics_data.get('saves_30d', 0)))
        with col4:
            st.metric("Клики на пины", format_compact(analytics_data.get('pin_clicks_30d', 0)))
        st.markdown("---")
        st.markdown("### Показатели эффективности")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Engagement Rate", f"{analytics_data.get('engagement_rate_30d', 0):.2f}%")
        with col2:
            st.metric("Save Rate", f"{analytics_data.get('save_rate_30d', 0):.2f}%")
        with col3:
            st.metric("Pin Click Rate", f"{analytics_data.get('pin_click_rate_30d', 0):.2f}%")
        with col4:
            st.metric("Переходы", format_compact(analytics_data.get('outbound_clicks_30d', 0)))
        st.markdown("---")
        st.markdown("### Сравнение метрик")
        metrics_comparison = {
            'Метрика': ['Показы', 'Вовлечения', 'Сохранения', 'Клики'],
            'Значение': [
                analytics_data.get('impressions_30d', 0),
                analytics_data.get('engagements_30d', 0),
                analytics_data.get('saves_30d', 0),
                analytics_data.get('pin_clicks_30d', 0)
            ]
        }
        comparison_df = pd.DataFrame(metrics_comparison)
        chart = ChartBuilder.bar_chart(
            comparison_df,
            x='Метрика',
            y='Значение',
            title='Сравнение метрик за 30 дней',
            x_label='Метрика',
            y_label='Количество',
            color=PLATFORM_COLORS.get('pinterest', '#bd081c')
        )
        st.plotly_chart(chart, use_container_width=True)
        st.markdown("---")
        st.markdown("### Информация о профиле")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            username = analytics_data.get('username', 'N/A')
            st.metric("Username", username)
        with col2:
            business_name = analytics_data.get('business_name', 'N/A')
            st.metric("Business Name", business_name or "—")
        with col3:
            board_count = analytics_data.get('board_count', 0)
            st.metric("Досок", board_count)
        with col4:
            following_count = analytics_data.get('following_count', 0)
            st.metric("Подписок", following_count)
        st.markdown("---")
        st.markdown("### Средние показатели на пин")
        avg_impressions = analytics_data.get('avg_impressions_per_pin', 0)
        avg_saves = analytics_data.get('avg_saves_per_pin', 0)
        avg_clicks = analytics_data.get('avg_clicks_per_pin', 0)
        if avg_impressions or avg_saves or avg_clicks:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Средние показы/пин", format_compact(int(avg_impressions)))
            with col2:
                st.metric("Средние сохранения/пин", format_compact(int(avg_saves)))
            with col3:
                st.metric("Средние клики/пин", format_compact(int(avg_clicks)))
        else:
            st.info("Данные о средних показателях на пин недоступны.")
    else:
        st.info("""
        📊 **Нет данных аналитики за 30 дней**
        Для получения аналитики:
        - Убедитесь, что аккаунт подключен через OAuth
        - Запустите сбор метрик через API
        - Pinterest Analytics API требует Business Account
        """)
st.markdown("---")
st.subheader("📋 Таблица метрик")
render_metrics_table(metrics_df)
st.markdown("---")
st.caption(f"Последнее обновление: {datetime.now().strftime('%d.%m.%Y %H:%M')}")
st.caption("📌 Pinterest API v5 OAuth 2.0 | Token encryption: Fernet AES-128")
