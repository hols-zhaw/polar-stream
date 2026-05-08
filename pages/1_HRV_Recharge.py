"""
1_HRV_Recharge.py
─────────────────
Layer 5 — HRV & Nightly Recharge Page

Displays heart rate variability trends, recovery scores, and recharge status.
Uses per-user session state for data isolation (safe for multi-user deployment).
"""

import streamlit as st
import pandas as pd

from data.cache import load_nightly_recharge
from analysis.hrv import add_rolling_average, flag_low_hrv, calculate_recovery_score
from viz.charts_hrv import (
    hrv_timeseries,
    recovery_score_chart,
    recharge_status_chart,
    hrv_distribution,
)

# ── Page Configuration ───────────────────────────────────────────────────────
st.set_page_config(
    page_title="HRV & Recharge | Polar Stream",
    page_icon="🫀",
    layout="wide",
)

st.title("🫀 HRV & Nightly Recharge")

# ── Data Loading (per-user session state) ────────────────────────────────────
def get_data():
    """
    Load data with per-user session caching.
    Uses st.session_state to isolate data between users (not shared).
    """
    if "nightly_recharge" not in st.session_state:
        with st.spinner("Loading HRV data from Polar API..."):
            try:
                st.session_state.nightly_recharge = load_nightly_recharge()
            except Exception as e:
                st.error(f"Failed to load data: {e}")
                st.info(
                    "Make sure you've:\n"
                    "1. Created `config.yml` from `config.example.yml`\n"
                    "2. Run `python -m auth.polar_auth` to authorize\n"
                    "3. Synced your Polar watch recently"
                )
                st.stop()
    return st.session_state.nightly_recharge


# ── Controls ──────────────────────────────────────────────────────────────────
col1, col2, col3 = st.columns([2, 2, 1])

with col1:
    days_to_show = st.slider(
        "Show last N days", min_value=7, max_value=365, value=30, step=7
    )

with col2:
    show_rolling = st.checkbox("Show 7-day rolling average", value=True)

with col3:
    if st.button("🔄 Refresh", help="Fetch latest data from Polar API"):
        del st.session_state.nightly_recharge
        st.rerun()

# ── Load and Process Data ─────────────────────────────────────────────────────
df = get_data()

if df.empty:
    st.warning("No nightly recharge data available. Sync your Polar watch and try again.")
    st.stop()

# Apply analysis functions (pure transformations)
df = add_rolling_average(df, "hrv_avg_ms", window=7)
df = flag_low_hrv(df, threshold_percentile=20)
df = calculate_recovery_score(df)

# Filter to selected date range (date-based, not row-count)
cutoff = df["date"].max() - pd.Timedelta(days=days_to_show)
filtered_df = df[df["date"] > cutoff]

start_date = filtered_df["date"].min().strftime("%b %d") if not filtered_df.empty else "—"
end_date = filtered_df["date"].max().strftime("%b %d") if not filtered_df.empty else "—"
st.caption(f"Showing {len(filtered_df)} days · {start_date} → {end_date}")

# ── Metrics Summary ───────────────────────────────────────────────────────────
st.subheader("📊 Summary Metrics")

metric_cols = st.columns(4)

with metric_cols[0]:
    latest_hrv = filtered_df["hrv_avg_ms"].iloc[-1] if not filtered_df.empty else 0
    avg_hrv = filtered_df["hrv_avg_ms"].mean()
    delta_hrv = latest_hrv - avg_hrv
    st.metric(
        "Latest HRV",
        f"{latest_hrv:.0f} ms",
        f"{delta_hrv:+.0f} ms from avg",
        delta_color="normal",
    )

with metric_cols[1]:
    avg_ans = filtered_df["ans_charge"].mean()
    st.metric("Avg ANS Charge", f"{avg_ans:.1f}/10")

with metric_cols[2]:
    low_recovery_days = filtered_df["low_recovery"].sum()
    low_recovery_pct = (low_recovery_days / len(filtered_df)) * 100 if not filtered_df.empty else 0
    st.metric(
        "Low Recovery Days",
        f"{low_recovery_days}",
        f"{low_recovery_pct:.0f}% of period",
        delta_color="inverse",
    )

with metric_cols[3]:
    latest_recovery = filtered_df["recovery_score"].iloc[-1] if not filtered_df.empty else 0
    st.metric("Latest Recovery Score", f"{latest_recovery:.0f}/100")

st.divider()

# ── Visualizations ────────────────────────────────────────────────────────────
st.subheader("📈 HRV Trends")

tab1, tab2, tab3 = st.tabs(["Time Series", "Recovery Score", "Recharge Status"])

with tab1:
    fig_hrv = hrv_timeseries(filtered_df, show_rolling=show_rolling)
    st.plotly_chart(fig_hrv, width="stretch")
    
    with st.expander("ℹ️ About HRV"):
        st.markdown("""
        **Heart Rate Variability (HRV)** measures the variation in time between heartbeats.
        Higher HRV generally indicates better recovery and readiness to train.
        
        - **Daily HRV**: Raw measurement from last night
        - **7-day average**: Smoothed trend line
        - **Low recovery**: Days in bottom 20% of your HRV range
        """)

with tab2:
    fig_recovery = recovery_score_chart(filtered_df)
    st.plotly_chart(fig_recovery, width="stretch")
    
    with st.expander("ℹ️ About Recovery Score"):
        st.markdown("""
        **Recovery Score** combines HRV and ANS Charge into a 0-100 scale:
        
        - **0-40**: Poor recovery (consider rest or light training)
        - **41-70**: Moderate recovery (normal training okay)
        - **71-100**: Excellent recovery (ready for hard training)
        """)

with tab3:
    fig_status = recharge_status_chart(filtered_df)
    st.plotly_chart(fig_status, width="stretch")
    
    with st.expander("ℹ️ About Nightly Recharge"):
        st.markdown("""
        **Nightly Recharge** is Polar's composite recovery metric combining:
        
        - **ANS Charge**: Autonomic nervous system recovery
        - **Sleep Charge**: Sleep quality and quantity
        
        Status levels: Very Poor → Poor → Compromised → Sustained → Very Good
        """)

# ── Distribution Analysis ─────────────────────────────────────────────────────
st.divider()
st.subheader("📊 HRV Distribution")

col_left, col_right = st.columns([2, 1])

with col_left:
    fig_dist = hrv_distribution(filtered_df)
    st.plotly_chart(fig_dist, width="stretch")

with col_right:
    st.markdown("### Statistics")
    hrv_stats = filtered_df["hrv_avg_ms"].describe()
    st.dataframe(
        pd.DataFrame(
            {
                "Metric": ["Mean", "Median", "Std Dev", "Min", "Max"],
                "Value (ms)": [
                    f"{hrv_stats['mean']:.1f}",
                    f"{filtered_df['hrv_avg_ms'].median():.1f}",
                    f"{hrv_stats['std']:.1f}",
                    f"{hrv_stats['min']:.1f}",
                    f"{hrv_stats['max']:.1f}",
                ],
            }
        ),
        hide_index=True,
        width="stretch",
    )
    
    st.markdown("### Data Coverage")
    st.metric("Total Days", len(filtered_df))
    st.metric("Date Range", f"{filtered_df['date'].min().strftime('%Y-%m-%d')} to {filtered_df['date'].max().strftime('%Y-%m-%d')}")

# ── Raw Data (collapsible) ────────────────────────────────────────────────────
with st.expander("🔍 View Raw Data"):
    st.dataframe(
        filtered_df[
            [
                "date",
                "hrv_avg_ms",
                "ans_charge",
                "hr_avg",
                "sleep_charge",
                "recharge_status",
                "recovery_score",
            ]
        ].sort_values("date", ascending=False),
        hide_index=True,
        width="stretch",
    )
