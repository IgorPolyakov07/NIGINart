import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from typing import List, Optional
from dashboard.config import CHART_HEIGHT
from dashboard.utils.constants import PLATFORM_COLORS
class ChartBuilder:
    THEME = {
        'font': {'family': 'Arial, sans-serif', 'size': 12},
        'plot_bgcolor': '#ffffff',
        'paper_bgcolor': '#ffffff',
        'margin': {'l': 40, 'r': 40, 't': 40, 'b': 40}
    }
    @staticmethod
    def line_chart(
        df: pd.DataFrame,
        x: str,
        y: str,
        title: str,
        y_label: str,
        color: str = '#1f77b4'
    ) -> go.Figure:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df[x],
            y=df[y],
            mode='lines+markers',
            line=dict(color=color, width=2),
            marker=dict(size=6),
            hovertemplate='%{x}<br>%{y:,.0f}<extra></extra>'
        ))
        fig.update_layout(
            title=title,
            xaxis_title='',
            yaxis_title=y_label,
            **ChartBuilder.THEME,
            hovermode='x unified',
            height=CHART_HEIGHT
        )
        return fig
    @staticmethod
    def multi_line_chart(
        df: pd.DataFrame,
        x: str,
        y_columns: List[str],
        title: str,
        y_label: str,
        legend_labels: Optional[List[str]] = None
    ) -> go.Figure:
        fig = go.Figure()
        colors = px.colors.qualitative.Set2
        for i, col in enumerate(y_columns):
            label = legend_labels[i] if legend_labels else col
            fig.add_trace(go.Scatter(
                x=df[x],
                y=df[col],
                name=label,
                mode='lines+markers',
                line=dict(width=2, color=colors[i % len(colors)]),
                marker=dict(size=5)
            ))
        fig.update_layout(
            title=title,
            xaxis_title='',
            yaxis_title=y_label,
            **ChartBuilder.THEME,
            legend=dict(orientation='h', y=-0.15),
            height=CHART_HEIGHT
        )
        return fig
    @staticmethod
    def bar_chart(
        df: pd.DataFrame,
        x: str,
        y: str,
        title: str,
        x_label: str,
        y_label: str = '',
        color: str = '#1f77b4'
    ) -> go.Figure:
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df[x],
            y=df[y],
            orientation='h',
            marker=dict(color=color),
            text=df[x],
            texttemplate='%{text:,.0f}',
            textposition='outside',
            hovertemplate='%{y}: %{x:,.0f}<extra></extra>'
        ))
        fig.update_layout(
            title=title,
            xaxis_title=x_label,
            yaxis_title=y_label,
            **ChartBuilder.THEME,
            yaxis={'categoryorder': 'total ascending'},
            height=CHART_HEIGHT
        )
        return fig
    @staticmethod
    def gauge_chart(
        value: float,
        title: str,
        max_value: float = 10.0,
        threshold_good: float = 5.0
    ) -> go.Figure:
        color = '#22c55e' if value >= threshold_good else '#f59e0b'
        fig = go.Figure(go.Indicator(
            mode='gauge+number',
            value=value,
            title={'text': title},
            number={'suffix': '%'},
            gauge={
                'axis': {'range': [0, max_value]},
                'bar': {'color': color},
                'steps': [
                    {'range': [0, threshold_good], 'color': '#fee2e2'},
                    {'range': [threshold_good, max_value], 'color': '#dcfce7'}
                ]
            }
        ))
        fig.update_layout(**ChartBuilder.THEME, height=300)
        return fig
