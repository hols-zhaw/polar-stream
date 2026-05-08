"""
2_Diagnostics.py
────────────────
Layer 5 — Diagnostics Page

Shows API connectivity status, user info, and available data endpoints.
Useful for troubleshooting API issues.
"""

import streamlit as st
from datetime import datetime, timedelta

from data.fetcher import fetch_user_info, fetch_available_exercises, fetch_nightly_recharge
from auth.polar_auth import get_token, get_user_id

# ── Page Configuration ───────────────────────────────────────────────────────
st.set_page_config(
    page_title="Diagnostics | Polar Stream",
    page_icon="🔍",
    layout="wide",
)

st.title("🔍 API Diagnostics")

# ── Get Token ─────────────────────────────────────────────────────────────────
try:
    token = get_token()
    user_id = get_user_id()
except Exception as e:
    st.error(f"Failed to load access token: {e}")
    st.info("Run: python -m auth.polar_auth")
    st.stop()

# ── User Information ──────────────────────────────────────────────────────────
st.header("👤 User Information")

with st.spinner("Fetching user info..."):
    try:
        user_info = fetch_user_info(token, user_id)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Polar User ID", user_info.get("polar-user-id", "N/A"))
        
        with col2:
            st.metric("Member ID", user_info.get("member-id", "N/A"))
        
        with col3:
            name = f"{user_info.get('first-name', '')} {user_info.get('last-name', '')}".strip()
            st.metric("Name", name or "N/A")
        
        with col4:
            reg_date = user_info.get("registration-date", "N/A")
            if reg_date != "N/A":
                reg_date = reg_date.split("T")[0]  # Strip time
            st.metric("Registered", reg_date)
        
        with st.expander("📋 Full User Info (JSON)"):
            st.json(user_info)
        
        st.success("✓ User info retrieved successfully")
        
    except Exception as e:
        st.error(f"Failed to fetch user info: {e}")
        st.warning(
            "The `/v3/users` endpoint might not support GET requests. "
            "This is normal - we successfully registered earlier. "
            "User ID: 60797740"
        )

st.divider()

# ── Available Exercises ───────────────────────────────────────────────────────
st.header("🏃 Available Exercises")

with st.spinner("Checking for available exercises..."):
    try:
        exercise_urls = fetch_available_exercises(token)
        
        st.code(f"Response type: {type(exercise_urls)}", language=None)
        st.code(f"Response content: {exercise_urls}", language=None)
        
        if exercise_urls and len(exercise_urls) > 0:
            st.success(f"✓ Found {len(exercise_urls)} exercise(s) ready to sync")
            
            st.info(
                "⚠️ **Note:** Exercise data is transactional. "
                "Each URL can only be accessed ONCE before it's deleted by Polar. "
                "The main app will fetch and cache these automatically."
            )
            
            with st.expander(f"📋 Exercise URLs ({len(exercise_urls)})"):
                for i, url in enumerate(exercise_urls, 1):
                    st.code(f"{i}. {url}", language=None)
        else:
            st.warning("No exercises available to sync. All exercises have been fetched or none exist.")
            st.info(
                "To generate new exercises:\n"
                "1. Complete a workout on your Polar device\n"
                "2. Sync your device with Polar Flow\n"
                "3. Wait a few minutes\n"
                "4. Refresh this page"
            )
        
    except Exception as e:
        st.error(f"Failed to fetch exercise list: {e}")
        st.code(str(type(e)) + ": " + str(e), language=None)
        
        import traceback
        with st.expander("🐛 Full Error Traceback"):
            st.code(traceback.format_exc(), language=None)

st.divider()

# ── Nightly Recharge Data ─────────────────────────────────────────────────────
st.header("🫀 Nightly Recharge Data")

st.markdown("**Testing nightly recharge endpoint with different date ranges...**")

# Try fetching from different date ranges
date_ranges = [
    ("Last 7 days", 7),
    ("Last 30 days", 30),
    ("Last 90 days", 90),
]

for label, days in date_ranges:
    with st.expander(f"🔍 {label}"):
        try:
            since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            until = datetime.now().strftime("%Y-%m-%d")
            
            st.code(f"Date range: {since} to {until}", language=None)
            
            with st.spinner(f"Fetching {label}..."):
                data = fetch_nightly_recharge(token, since, until)
            
            if data:
                st.success(f"✓ Found {len(data)} record(s)")
                
                # Show first record as sample
                st.markdown("**Sample record (first entry):**")
                st.json(data[0])
                
                # Show all dates
                dates = [record.get("date", "N/A") for record in data]
                st.markdown(f"**Available dates ({len(dates)}):**")
                st.write(", ".join(sorted(dates, reverse=True)))
                
            else:
                st.warning(f"No data found for {label}")
                
        except Exception as e:
            st.error(f"Failed to fetch {label}: {e}")
            st.code(str(e), language=None)

st.divider()

# ── API Connectivity Summary ──────────────────────────────────────────────────
st.header("📊 Summary")

st.markdown("""
**What to check if you see errors:**

1. **403 Forbidden:** User not registered properly
   - Run: `python -m auth.check_registration`

2. **401 Unauthorized:** Invalid or expired token
   - Run: `python -m auth.polar_auth` to re-authorize

3. **No nightly recharge data:** 
   - Make sure you wear your watch overnight with sleep tracking enabled
   - Sync your watch with Polar Flow after waking up
   - Wait 15-30 minutes for data to propagate
   - Note: Only data **after** AccessLink registration is available

4. **No exercises:**
   - Complete a workout and sync with Polar Flow
   - Exercise data is transactional (one-time fetch)

**Useful commands:**
```bash
# Re-authorize (if token issues)
python -m auth.polar_auth

# Check registration status
python -m auth.check_registration

# Run dashboard
streamlit run app.py
```
""")

# ── Refresh Button ────────────────────────────────────────────────────────────
st.divider()

col1, col2, col3 = st.columns([1, 1, 2])

with col1:
    if st.button("🔄 Refresh All", type="primary", width="stretch"):
        st.rerun()

with col2:
    if st.button("← Back to Home", width="stretch"):
        st.switch_page("app.py")
