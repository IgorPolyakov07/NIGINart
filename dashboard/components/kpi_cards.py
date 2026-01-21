import streamlit as st
from typing import Optional, Dict
from dashboard.utils.formatters import format_compact, format_number, format_percent
def render_kpi_card(
    label: str,
    value: float,
    delta: Optional[float] = None,
    format_type: str = 'number',
    delta_color: str = 'normal'
):
    if format_type == 'percent':
        formatted_value = format_percent(value)
    elif format_type == 'compact':
        formatted_value = format_compact(value)
    else:
        formatted_value = format_number(value)
    delta_str = None
    if delta is not None:
        if format_type == 'percent':
            delta_str = format_percent(delta)
        elif format_type == 'compact':
            delta_str = format_compact(delta, show_sign=True)
        else:
            delta_str = format_number(delta, decimals=0)
            if delta > 0:
                delta_str = f"+{delta_str}"
    st.metric(
        label=label,
        value=formatted_value,
        delta=delta_str,
        delta_color=delta_color
    )
def render_kpi_row(metrics: Dict):
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        m = metrics.get('followers', {})
        render_kpi_card(
            "Подписчики",
            m.get('value', 0),
            m.get('delta'),
            format_type='compact'
        )
    with col2:
        m = metrics.get('engagement_rate', {})
        render_kpi_card(
            "Вовлеченность",
            m.get('value', 0),
            m.get('delta'),
            format_type='percent'
        )
    with col3:
        m = metrics.get('posts', {})
        render_kpi_card(
            "Публикации",
            m.get('value', 0),
            m.get('delta'),
            format_type='number'
        )
    with col4:
        if 'views' in metrics:
            m = metrics['views']
            label = "Просмотры"
        elif 'likes' in metrics:
            m = metrics['likes']
            label = "Лайки"
        else:
            m = {}
            label = "—"
        render_kpi_card(
            label,
            m.get('value', 0),
            m.get('delta'),
            format_type='compact'
        )
