"""
charts_hrv.py
─────────────
Layer 4 — HRV Visualization
Pure charting functions: DataFrame → Plotly Figure.

No Streamlit import. No data fetching. No business logic.
Fully testable standalone.
"""

import plotly.graph_objects as go
import pandas as pd
from viz.theme import COLORS, LAYOUT_DEFAULTS, RECHARGE_STATUS_COLORS


def hrv_timeseries(df: pd.DataFrame, show_rolling: bool = True) -> go.Figure:
    """
    Render daily HRV average with optional rolling average overlay.
    
    Args:
        df: DataFrame with columns [date, hrv_avg_ms, hrv_avg_ms_rolling7 (optional)]
        show_rolling: Whether to show rolling average line (default: True)
        
    Returns:
        Plotly Figure object
    """
    if "date" not in df.columns or "hrv_avg_ms" not in df.columns:
        raise ValueError("DataFrame must contain 'date' and 'hrv_avg_ms' columns")
    
    fig = (
        go.Figure()
        # Daily HRV (scatter + line)
        .add_trace(
            go.Scatter(
                x=df["date"],
                y=df["hrv_avg_ms"],
                mode="markers+lines",
                name="HRV avg (daily)",
                line=dict(color=COLORS["hrv"], width=1),
                marker=dict(size=4, color=COLORS["hrv"]),
                opacity=0.6,
                hovertemplate="<b>%{x|%Y-%m-%d}</b><br>HRV: %{y:.0f} ms<extra></extra>",
            )
        )
    )

    # Rolling average (if column exists and enabled)
    if show_rolling and "hrv_avg_ms_rolling7" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df["date"],
                y=df["hrv_avg_ms_rolling7"],
                mode="lines",
                name="7-day average",
                line=dict(color=COLORS["hrv"], width=3),
                hovertemplate="<b>%{x|%{Y-%m-%d}</b><br>7-day avg: %{y:.0f} ms<extra></extra>",
            )
        )

    return fig.update_layout(
        **LAYOUT_DEFAULTS,
        title="Heart Rate Variability (HRV)",
        xaxis_title="Date",
        yaxis_title="HRV (ms)",
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )


def recovery_score_chart(df: pd.DataFrame) -> go.Figure:
    """
    Render composite recovery score over time.
    
    Args:
        df: DataFrame with columns [date, recovery_score]
        
    Returns:
        Plotly Figure object
    """
    if "date" not in df.columns or "recovery_score" not in df.columns:
        raise ValueError("DataFrame must contain 'date' and 'recovery_score' columns")
    
    # Color gradient based on score
    colors = df["recovery_score"].apply(
        lambda x: COLORS["good"] if x > 70 else (COLORS["training"] if x > 40 else COLORS["poor"])
    )

    return (
        go.Figure()
        .add_trace(
            go.Bar(
                x=df["date"],
                y=df["recovery_score"],
                name="Recovery Score",
                marker=dict(color=colors, line=dict(width=0)),
                hovertemplate="<b>%{x|%Y-%m-%d}</b><br>Recovery: %{y:.0f}/100<extra></extra>",
            )
        )
        .update_layout(
            **LAYOUT_DEFAULTS,
            title="Recovery Score (HRV + ANS Charge)",
            xaxis_title="Date",
            yaxis_title="Recovery Score",
            showlegend=False,
        )
        .update_yaxes(range=[0, 100])
    )


def recharge_status_chart(df: pd.DataFrame) -> go.Figure:
    """
    Render nightly recharge status as colored blocks.
    
    Args:
        df: DataFrame with columns [date, recharge_status]
        
    Returns:
        Plotly Figure object
    """
    if "date" not in df.columns or "recharge_status" not in df.columns:
        raise ValueError("DataFrame must contain 'date' and 'recharge_status' columns")
    
    # Map status to numeric values for visualization
    status_values = {
        "very_poor": 1,
        "poor": 2,
        "compromised": 3,
        "sustained": 4,
        "very_good": 5,
    }
    
    df = df.copy()
    df["status_value"] = df["recharge_status"].map(status_values)
    df["status_color"] = df["recharge_status"].map(RECHARGE_STATUS_COLORS)
    
    return (
        go.Figure()
        .add_trace(
            go.Bar(
                x=df["date"],
                y=df["status_value"],
                name="Recharge Status",
                marker=dict(color=df["status_color"], line=dict(width=0)),
                hovertemplate="<b>%{x|%Y-%m-%d}</b><br>Status: %{customdata}<extra></extra>",
                customdata=df["recharge_status"].str.replace("_", " ").str.title(),
            )
        )
        .update_layout(
            **LAYOUT_DEFAULTS,
            title="Nightly Recharge Status",
            xaxis_title="Date",
            yaxis_title="",
            showlegend=False,
        )
        .update_yaxes(
            tickvals=[1, 2, 3, 4, 5],
            ticktext=["Very Poor", "Poor", "Compromised", "Sustained", "Very Good"],
        )
    )


def hrv_distribution(df: pd.DataFrame) -> go.Figure:
    """
    Render HRV distribution as histogram with KDE overlay.
    
    Args:
        df: DataFrame with column [hrv_avg_ms]
        
    Returns:
        Plotly Figure object
    """
    if "hrv_avg_ms" not in df.columns:
        raise ValueError("DataFrame must contain 'hrv_avg_ms' column")
    
    median = df["hrv_avg_ms"].median()
    
    return (
        go.Figure()
        .add_trace(
            go.Histogram(
                x=df["hrv_avg_ms"],
                nbinsx=30,
                name="HRV Distribution",
                marker=dict(color=COLORS["hrv"], opacity=0.7),
                hovertemplate="HRV: %{x:.0f} ms<br>Count: %{y}<extra></extra>",
            )
        )
        .add_vline(
            x=median,
            line=dict(color=COLORS["ans_charge"], width=2, dash="dash"),
            annotation_text=f"Median: {median:.0f} ms",
            annotation_position="top",
        )
        .update_layout(
            **LAYOUT_DEFAULTS,
            title="HRV Distribution",
            xaxis_title="HRV (ms)",
            yaxis_title="Frequency",
            showlegend=False,
            bargap=0.1,
        )
    )
