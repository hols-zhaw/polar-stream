"""
Polar Stream — Personal Analytics Dashboard
===========================================
Main entry point for Streamlit multi-page app.

Layer 5 — Presentation (Streamlit)
"""

import streamlit as st

# ── Page Configuration ───────────────────────────────────────────────────────
st.set_page_config(
    page_title="Polar Stream",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Main Page ─────────────────────────────────────────────────────────────────
st.title("📊 Polar Stream")
st.markdown("""
Welcome to **Polar Stream** — your personal analytics dashboard for Polar sports watch data.

### Available Pages

- **🫀 HRV & Recharge** — Nightly heart rate variability, ANS charge, and recovery trends
- **😴 Sleep** — Sleep quality, stages, and duration analysis (coming soon)
- **🏃 Training** — Exercise history, HR zones, and training load (coming soon)
- **📈 Correlations** — Cross-metric analysis and insights (coming soon)

### Getting Started

1. Navigate to a page using the sidebar
2. Data is loaded automatically from your Polar account
3. Use the refresh button to fetch new data after syncing your watch

---

**Data Source:** Polar AccessLink API v3  
**Privacy:** All data is stored locally and never shared
""")

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("About")
    st.markdown("""
    Polar Stream pulls your biometric data from the Polar AccessLink API
    and presents custom visualizations beyond what Polar Flow offers.
    
    **Architecture:**
    - 🔐 OAuth2 authentication
    - 💾 Local Parquet cache
    - 📊 Interactive Plotly charts
    - 🧪 Pure, testable analysis functions
    """)
    
    st.divider()
    
    st.caption("Built with Streamlit • Powered by Polar AccessLink API")
