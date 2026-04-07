# Polar Personal Analytics Dashboard
**Project Planning & Architecture Report**
*Last updated: March 2026*

---

## Table of Contents

1. [Idea & Goals](#1-idea--goals)
2. [Polar AccessLink API – Overview](#2-polar-accesslink-api--overview)
3. [Existing Libraries, Projects & Solutions](#3-existing-libraries-projects--solutions)
4. [Key Constraints & Gotchas](#4-key-constraints--gotchas)
5. [Proposed Architecture](#5-proposed-architecture)
6. [Project Structure](#6-project-structure)
7. [Implementation Roadmap](#7-implementation-roadmap)
8. [Open Questions](#8-open-questions)

---

## 1. Idea & Goals

### Background

The user owns a Polar sports watch (e.g. Vantage V3) that continuously measures biometric data such as heart rate, HRV, sleep stages and training performance. Data is synced from the watch to the **Polar Flow** mobile app via Bluetooth and subsequently stored in the Polar Cloud. The goal is to build a **personal analytics dashboard** that pulls this data via the Polar AccessLink API and presents custom visualizations not available in the stock Polar Flow app.

### Primary Use Cases

- **Nightly HRV time series**: Visualize ANS charge, HRV average, and resting heart rate trends over weeks/months to understand recovery patterns.
- **Training performance tracking**: Analyze exercise sessions by sport type, heart rate zones, duration, and load over time.
- **Sleep quality trends**: Track sleep score, deep/REM/light sleep ratios, and correlate with training load or HRV.
- **Nightly Recharge overview**: Monitor the composite Recharge score (sleep charge + ANS charge) over time.

### Future Use Cases (Nice-to-Have)

- Correlation analysis: e.g. training load vs. next-day HRV
- Weekly/monthly summary reports
- Optional: Open the app to other users (multi-user, with OAuth per user)

### Technology Goals

- **Simple to build and maintain** — no unnecessary complexity
- **Personal use first**, but architecture should allow future public deployment
- **Runs locally** and optionally on Streamlit Cloud
- **Responsive** — usable on desktop browser and iPhone/iPad

---

## 2. Polar AccessLink API – Overview

### API Versions

| Version | URL | Notes |
|---|---|---|
| **v3** (stable) | `https://www.polaraccesslink.com/v3/` | Main API, used in all official examples |
| **v4** (Dynamic API, newer) | `https://www.polaraccesslink.com/v4/` | Newer endpoints, e.g. extended nightly recharge with samples |

**Recommendation:** Use v3 as the base, add v4 endpoints where needed (e.g. HRV samples).

### Authentication

The API uses **OAuth2 Authorization Code Flow**:

```
1. User is redirected to:
   https://flow.polar.com/oauth2/authorization?response_type=code&client_id=YOUR_ID&scope=accesslink.read_all

2. After user approves → redirect back to your callback URL with ?code=AUTH_CODE

3. Exchange code for access token:
   POST https://polarremote.com/v2/oauth2/token
   (Basic Auth: client_id:client_secret, body: grant_type=authorization_code&code=AUTH_CODE)

4. Response: { "access_token": "...", "x_user_id": "..." }

5. Register user (required once before any data call):
   POST https://www.polaraccesslink.com/v3/users
   Authorization: Bearer ACCESS_TOKEN
```

**Important:** Access tokens **do not expire** unless explicitly revoked. This means the OAuth flow only needs to be performed **once**, and the token can be stored in a local file (e.g. `config.yml`) for all future use.

### Available Data Endpoints (v3)

| Endpoint | Data |
|---|---|
| `GET /v3/users/{user-id}` | Profile: name, gender, weight, height, VO2max |
| `GET /v3/users/{user-id}/physical-information` | Weight, resting HR, VO2max history |
| `GET /v3/users/{user-id}/sleep` | Sleep score, stages (deep/light/REM), duration, interruptions |
| `GET /v3/users/{user-id}/nightly-recharge` | ANS charge, HRV avg, HR avg, breathing rate, sleep charge, Recharge status |
| `GET /v3/exercises/{exerciseId}` | Sport, duration, HR zones, calories, distance |
| `GET /v3/exercises/{exerciseId}/heart-rate-zones` | Detailed HR zone breakdown |
| `GET /v3/exercises/{exerciseId}/tcx` | Full TCX workout file (GPS + HR time series) |
| `GET /v3/notifications` | Pull notifications for new data events |

### v4 Extras (Dynamic API)

- `GET /v4/data/nightly-recharge?from=...&to=...&features=samples` — Includes 5-minute HRV samples during sleep (requires special feature activation)
- `GET /v4/data/sleep?features=hypnogram` — Detailed sleep hypnogram

### Data Freshness / Webhooks

The API provides a **webhook system**: Polar pushes a POST request to your server URL when new data is available (e.g. after the user syncs the watch). This requires a publicly reachable server.

**For personal local use:** This is optional. A manual refresh button (or periodic polling) in the app is sufficient, since data is only created after a watch sync anyway.

### Critical Limitation: No Historical Data

The AccessLink API **only delivers data that has been synced after your API client was registered**. There is no bulk export of historical data via the API. Mitigation: export older data manually from Polar Flow as JSON/CSV, or use the FIT/TCX download tools. Once the app is running, all new data will be captured automatically.

---

## 3. Existing Libraries, Projects & Solutions

### Official

#### `polarofficial/accesslink-example-python` (GitHub)
> https://github.com/polarofficial/accesslink-example-python

The official reference implementation. Provides:
- `accesslink/` — reusable Python client wrapper around the API
- `example_web_app.py` — Flask-based web app with OAuth callback handler on `localhost:5000`
- `example_console_app.py` — Interactive CLI for manual data fetching
- `authorization_callback_server.py` — Standalone callback server for the one-time OAuth flow
- Token storage in `config.yml` / `usertokens.yml`

**Key takeaway:** The OAuth flow and data access are cleanly separated. The callback server handles auth once; afterwards all calls just use the saved token.

### Community Projects

#### `polar_to_googlesheets` (GitHub Fork)
> https://github.com/[various forks]

A fork of the official example that pipes Nightly Recharge and Sleep data directly into Google Sheets. Useful as a **field mapping reference** — shows exactly which API response fields map to which metrics (ANS Charge, Beat-to-Beat Average, HRV Average, Sleep Score, REM/Deep/Light Sleep etc.).

#### `polarbeer` by roessland (GitHub)
> https://github.com/roessland/polarbeer

Proof-of-concept for exporting Polar data to **InfluxDB** and visualizing via **Grafana**. Explores computing training load metrics (TSS, CTL — Chronic Training Load). Good inspiration for time-series storage approach, though Grafana/InfluxDB adds unnecessary complexity for a personal Streamlit app.

#### `polar-accesslink` (PyPI)
> `pip install polar-accesslink`

A packaged fork of the official client. Installable directly without copying the GitHub source. Provides the same `AccessLink` class. Convenient starting point.

#### Polar AccessLink MCP Server
> https://github.com/mbentham/polarmcp

A Model Context Protocol (MCP) server wrapping the AccessLink v3 API. Makes Polar data accessible to AI assistants like Claude. Covers: exercises, daily activity, physical info, sleep, nightly recharge, continuous heart rate. **Useful as an API usage reference**, not directly relevant to the dashboard project.

### Charting Libraries Considered

| Library | Notes |
|---|---|
| **Plotly** | Interactive, zoom/hover, first-class in Streamlit via `st.plotly_chart()` |
| **Altair** | Declarative, excellent for time series, `st.altair_chart()` |
| **streamlit-echarts** | Beautiful, mobile-friendly, via community component |
| Matplotlib | Static, avoid unless for quick prototyping |

---

## 4. Key Constraints & Gotchas

### OAuth2: One-Time Setup

The OAuth flow requires a redirect callback URL. For local development, `http://localhost:5000/oauth2_callback` is used. The one-time setup flow is:

```bash
# Step 1: Start the callback server (from the official repo)
python authorization_callback_server.py

# Step 2: Open in browser:
# https://flow.polar.com/oauth2/authorization?response_type=code&client_id=YOUR_CLIENT_ID

# Step 3: Authorize → token saved to config.yml automatically
# Step 4: Stop the callback server — never needed again
```

After this, the Streamlit app just loads the token from `config.yml` and uses it directly. **No OAuth complexity inside Streamlit.**

### User Registration

After the first token exchange, the user must be registered once:
```python
# Must be called exactly once before accessing any data
accesslink.users.register(access_token=token)
```

If skipped, all API calls return `403 Access Denied`.

### Transactional vs. Non-Transactional Endpoints

| Type | Behavior | Endpoints |
|---|---|---|
| **Transactional** | Data is **deleted after fetch** — can only be read once | Exercises, Activity Summary, Physical Info (via transactions) |
| **Non-Transactional** | Data remains available, can be re-fetched anytime | Sleep, Nightly Recharge, User Info |

**Implication:** Transactional data (exercises) **must be persisted locally** the first time it is fetched — you cannot go back. Non-transactional data (sleep, HRV) can be re-fetched, but caching is still advisable for performance.

### No Raw RR Intervals

The AccessLink API does **not** expose raw RR interval data. The available HRV metric is a **nightly HRV average** (in ms) from the Nightly Recharge endpoint. For true HRV analysis (RMSSD, frequency domain etc.) from RR intervals, a third-party app like Elite HRV would be needed — this is a Polar platform limitation.

---

## 5. Proposed Architecture

### Overview

```
[Polar Watch]
     │ Bluetooth sync
     ▼
[Polar Flow App / Cloud]
     │ AccessLink API v3/v4 (HTTPS + OAuth2 Bearer Token)
     ▼
┌─────────────────────────────────────────┐
│           Python Backend Layer          │
│                                         │
│  accesslink_client.py                   │
│    → fetch_sleep()                      │
│    → fetch_nightly_recharge()           │
│    → fetch_exercises()                  │
│                                         │
│  cache.py                               │
│    → Parquet files (persistent)         │
│    → @st.cache_data (in-memory/session) │
└─────────────────────────────────────────┘
     │ Pandas DataFrames
     ▼
┌─────────────────────────────────────────┐
│         Streamlit Frontend              │
│                                         │
│  app.py              ← Entry point      │
│  pages/                                 │
│    1_HRV_Recharge.py                    │
│    2_Sleep.py                           │
│    3_Training.py                        │
│    4_Correlations.py                    │
│                                         │
│  Plotly / Altair charts                 │
│  Tailwind-ish: Streamlit native layout  │
└─────────────────────────────────────────┘
     │ Browser (Desktop + Mobile Responsive)
     ▼
[localhost:8501] or [Streamlit Cloud]
```

### Technology Stack

| Layer | Technology | Rationale |
|---|---|---|
| **Language** | Python 3.11+ | Best ecosystem for data analysis; official Polar examples in Python |
| **API Client** | Official `accesslink/` module (from official repo) or `pip install polar-accesslink` | Battle-tested, wraps all endpoints cleanly |
| **Data Processing** | Pandas, NumPy | Standard for time series manipulation |
| **Persistent Cache** | **Parquet** (via `pandas.to_parquet`) | Compressed, fast, future-proof; readable by DuckDB, Spark etc. |
| **Session Cache** | `@st.cache_data(ttl=3600)` | Avoids re-reading disk on every Streamlit interaction |
| **Frontend** | **Streamlit** | Minimal code, native multi-page support, built-in Plotly/Altair integration |
| **Charts** | **Plotly** (primary) + Altair (secondary) | Interactive zoom/hover; great for time series |
| **Config/Secrets** | `config.yml` (local) / Streamlit Secrets (cloud) | Keeps credentials out of code |
| **Hosting (now)** | Local: `streamlit run app.py` | Zero infrastructure |
| **Hosting (later)** | Streamlit Cloud (free tier) | Push to GitHub → auto-deploy; Secrets management built in |

### Caching Strategy

```python
import streamlit as st
import pandas as pd
from pathlib import Path

CACHE_DIR = Path("cache")
CACHE_DIR.mkdir(exist_ok=True)

@st.cache_data(ttl=3600)
def load_nightly_recharge() -> pd.DataFrame:
    cache_file = CACHE_DIR / "nightly_recharge.parquet"
    if cache_file.exists():
        df = pd.read_parquet(cache_file)
    else:
        df = pd.DataFrame()  # empty fallback

    # Fetch only new data from API (since last cached date)
    last_date = df["date"].max() if not df.empty else "2020-01-01"
    new_data = fetch_from_polar(endpoint="nightly_recharge", since=last_date)

    if new_data:
        new_df = pd.DataFrame(new_data)
        df = pd.concat([df, new_df]).drop_duplicates("date")
        df.to_parquet(cache_file, index=False)

    return df
```

### Config File Structure

```yaml
# config.yml  (never commit to git — add to .gitignore)
client_id: "YOUR_CLIENT_ID"
client_secret: "YOUR_CLIENT_SECRET"
access_token: "YOUR_ACCESS_TOKEN"   # written by authorization_callback_server.py
user_id: "YOUR_POLAR_USER_ID"       # written by authorization_callback_server.py
```

---

## 6. Project Structure

```
polar-dashboard/
│
├── app.py                        # Streamlit entry point + sidebar navigation
├── config.yml                    # Credentials (gitignored)
├── requirements.txt
├── .gitignore
│
├── pages/
│   ├── 1_HRV_Recharge.py         # Nightly HRV & ANS charge time series
│   ├── 2_Sleep.py                # Sleep stages, score, duration trends
│   ├── 3_Training.py             # Exercise log, HR zones, load
│   └── 4_Correlations.py        # Cross-metric analysis (optional)
│
├── accesslink/                   # Copied from official repo (or installed via pip)
│   ├── accesslink.py
│   ├── oauth2.py
│   └── endpoints/
│
├── data/
│   ├── client.py                 # Wrapper: loads config, initializes AccessLink
│   ├── fetcher.py                # fetch_sleep(), fetch_nightly_recharge(), fetch_exercises()
│   └── cache.py                  # Parquet read/write + @st.cache_data decorators
│
├── cache/                        # Local Parquet files (gitignored)
│   ├── nightly_recharge.parquet
│   ├── sleep.parquet
│   └── exercises.parquet
│
├── auth/
│   └── authorization_callback_server.py  # Run once for OAuth setup
│
└── utils/
    └── charts.py                 # Reusable Plotly chart functions
```

---

## 7. Implementation Roadmap

### Phase 1 — OAuth Setup & Data Fetch (Day 1)

- [ ] Create API client at https://admin.polaraccesslink.com
- [ ] Copy `accesslink/` module and `authorization_callback_server.py` from official repo
- [ ] Run one-time OAuth flow → token saved to `config.yml`
- [ ] Write `data/fetcher.py`: test fetching sleep + nightly recharge manually
- [ ] Verify data fields (print raw JSON response)

### Phase 2 — Cache & Data Layer (Day 1–2)

- [ ] Implement Parquet cache in `data/cache.py`
- [ ] Write incremental fetch logic (only fetch since last cached date)
- [ ] Handle transactional exercise data: fetch once, always persist immediately

### Phase 3 — First Dashboard Page (Day 2–3)

- [ ] Set up `app.py` with Streamlit page config and sidebar
- [ ] Build `pages/1_HRV_Recharge.py`:
  - Time series chart: HRV avg + ANS charge over last 90 days
  - 7-day rolling average overlay
  - Color coding: Recharge status (very poor → very good)

### Phase 4 — Additional Pages (Week 1–2)

- [ ] `pages/2_Sleep.py`: Sleep score trend, stage breakdown (stacked bar)
- [ ] `pages/3_Training.py`: Exercise log table + HR zone charts per session
- [ ] Manual "Refresh Data" button in sidebar (triggers API fetch + cache update)

### Phase 5 — Streamlit Cloud Deployment (Week 2)

- [ ] Push repo to GitHub (with `config.yml` in `.gitignore`)
- [ ] Add secrets via Streamlit Cloud Secrets Manager
- [ ] Deploy and test on mobile (iPhone/iPad browser)

---

## 8. Open Questions

| Question | Notes |
|---|---|
| **HRV samples (5-min intervals)?** | Need to check if v4 `nightly-recharge?features=samples` is available for standard API clients (may require Polar partner approval) |
| **Historical data?** | API only delivers data from registration date onwards. Older data must be manually exported from Polar Flow. Consider a one-time import script. |
| **Webhook for near real-time?** | Not needed for personal use. If deployed publicly later, a small FastAPI backend (e.g. on Railway) can handle webhook ingestion. |
| **Multi-user (future)?** | Streamlit Cloud free tier has no built-in auth. Options: Streamlit `st.secrets` + password gate for small groups, or migrate to Next.js + FastAPI for full multi-user OAuth. |
| **GPX/route data?** | The `GET /v3/exercises/{id}/tcx` endpoint returns full GPS tracks. Could be added as a map view (e.g. via `streamlit-folium`) in a later phase. |
