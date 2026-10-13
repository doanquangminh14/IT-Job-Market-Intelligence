import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
try:
    from config import CHART_THEME
except ImportError:
    from app.config import CHART_THEME

def _apply_modern_layout(fig, title=""):
    """Áp dụng thiết kế đồ họa chuẩn SaaS cho biểu đồ Plotly."""
    fig.update_layout(
        title=dict(
            text=f"<b>{title}</b>" if title else "",
            font=dict(size=14, color="#0f172a", family="Plus Jakarta Sans, sans-serif"),
            x=0.01,
            y=0.98
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Plus Jakarta Sans, sans-serif", color="#475569", size=12),
        hoverlabel=dict(
            bgcolor="#0f172a",
            font_color="#ffffff",
            font_size=12,
            font_family="Plus Jakarta Sans, sans-serif"
        ),
        margin=dict(l=20, r=20, t=50, b=20),
    )
    fig.update_xaxes(
        gridcolor="#f1f5f9",
        zerolinecolor="#e2e8f0",
        tickfont=dict(color="#64748b", size=11)
    )
    fig.update_yaxes(
        gridcolor="#f1f5f9",
        zerolinecolor="#e2e8f0",
        tickfont=dict(color="#64748b", size=11)
    )
    return fig

def plot_bar_horizontal(df, x_col, y_col, title, color_col=None, text_auto=True):
    """Vẽ biểu đồ cột ngang trực quan phong cách hiện đại."""
    fig = px.bar(
        df,
        x=x_col,
        y=y_col,
        orientation='h',
        color=color_col or x_col,
        color_continuous_scale="Blues",
        text_auto=text_auto
    )
    fig.update_traces(
        marker=dict(line=dict(width=0)),
        textposition='outside'
    )
    fig.update_layout(
        yaxis=dict(autorange="reversed"),
        xaxis_title="",
        yaxis_title="",
        showlegend=False,
        coloraxis_showscale=False
    )
    return _apply_modern_layout(fig, title)

def plot_donut(df, names_col, values_col, title):
    """Vẽ biểu đồ Donut phân bố tỷ lệ hiện đại."""
    fig = px.pie(
        df,
        names=names_col,
        values=values_col,
        hole=0.55,
        color_discrete_sequence=CHART_THEME["palette"]
    )
    fig.update_traces(
        textposition='inside',
        textinfo='percent+label',
        marker=dict(line=dict(color='#ffffff', width=2))
    )
    fig.update_layout(
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5)
    )
    return _apply_modern_layout(fig, title)

def plot_stacked_bar(df, x_col, y_col, color_col, title, barmode='stack'):
    """Vẽ biểu đồ cột xếp chồng hoặc nhóm (Stacked/Grouped Bar)."""
    fig = px.bar(
        df,
        x=x_col,
        y=y_col,
        color=color_col,
        barmode=barmode,
        color_discrete_sequence=[CHART_THEME["primary"], CHART_THEME["secondary"]]
    )
    fig.update_layout(
        xaxis_title="",
        yaxis_title="Số lượng",
        legend_title="Phân loại",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    return _apply_modern_layout(fig, title)

def plot_heatmap(matrix_df, title):
    """Vẽ bản đồ nhiệt (Heatmap) cho ma trận đồng xuất hiện."""
    fig = px.imshow(
        matrix_df,
        text_auto=True,
        aspect="auto",
        color_continuous_scale="Viridis"
    )
    return _apply_modern_layout(fig, title)
