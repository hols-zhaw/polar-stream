# Polar Dashboard — Architecture Deep Dive
**OAuth Libraries & Layered Architecture**
*Addendum to: polar_dashboard_project.md*

---

## Table of Contents

1. [OAuth2 Library Comparison](#1-oauth2-library-comparison)
2. [Recommended OAuth Implementation](#2-recommended-oauth-implementation)
3. [Layered Architecture: Separation of Concerns](#3-layered-architecture-separation-of-concerns)
4. [Layer Specifications](#4-layer-specifications)
5. [Interface Contracts Between Layers](#5-interface-contracts-between-layers)
6. [Final Project Structure](#6-final-project-structure)

---

## 1. OAuth2 Library Comparison

Four realistic options exist for the one-time OAuth2 authorization flow with Polar.

### 1.1 Overview

| | **oauthlib** | **requests-oauthlib** | **authlib** | **Manual (requests)** |
|---|---|---|---|---|
| **Level of abstraction** | Low (RFC primitives) | Medium | High | None |
| **Dependencies** | None | `requests` + `oauthlib` | None (optional `requests` / `httpx`) | `requests` only |
| **Sync support** | ✅ | ✅ | ✅ | ✅ |
| **Async support** | ❌ | ❌ | ✅ (`httpx`) | Only with `httpx` |
| **Framework coupling** | None | None | Optional (Flask/Django/Starlette) | None |
| **PKCE support** | ✅ Manual | ✅ | ✅ Built-in | Manual |
| **Token storage** | ❌ DIY | ❌ DIY | ❌ DIY | ❌ DIY |
| **Maintenance status** | Active | Active (v2, Mar 2024) | Active (v1.6.x) | — |
| **Lines of code needed** | ~60 | ~25 | ~20 | ~40 |
| **Architecturally isolated?** | ✅ | ✅ | ✅ | ✅ |

### 1.2 `oauthlib` — Low-Level RFC Primitives

`oauthlib` implements the OAuth2 specification directly, with no HTTP client coupling.
It provides the logic (URL construction, token parsing) but requires you to handle HTTP yourself.

```python
from oauthlib.oauth2 import WebApplicationClient

client = WebApplicationClient(client_id)

# Step 1: Build authorization URL
uri = client.prepare_request_uri(
    "https://flow.polar.com/oauth2/authorization",
    redirect_uri="http://localhost:5000/callback",
    scope=["accesslink.read_all"]
)

# Step 2: After redirect, parse callback and exchange for token
import requests, base64

token_response = requests.post(
    "https://polarremote.com/v2/oauth2/token",
    auth=(client_id, client_secret),
    data={"grant_type": "authorization_code", "code": code}
)
client.parse_request_body_response(token_response.text)
# token now in: client.token["access_token"]
```

**Assessment:** Most explicit and dependency-free, but more boilerplate. Good for understanding exactly what happens. Not ideal for rapid implementation.

### 1.3 `requests-oauthlib` — Drop-In for `requests`

Best for simple client flows when you already use `requests`. Integrates directly with `requests.Session` and provides straightforward helpers for OAuth2 Authorization Code flow.

```python
from requests_oauthlib import OAuth2Session

# Step 1: Build authorization URL
oauth = OAuth2Session(client_id, redirect_uri=redirect_uri, scope=["accesslink.read_all"])
auth_url, state = oauth.authorization_url("https://flow.polar.com/oauth2/authorization")

# Step 2: Exchange code for token
token = oauth.fetch_token(
    "https://polarremote.com/v2/oauth2/token",
    authorization_response=callback_url,
    client_secret=client_secret
)
# token["access_token"] is now available
```

**Assessment:** Cleanest fit for the Polar use case. Minimal, well-maintained, and fully framework-independent. The `OAuth2Session` object itself can also be reused for all subsequent API calls (handles `Authorization: Bearer` headers automatically).

### 1.4 `authlib` — Full-Featured, Framework-Optional

`authlib` provides both `OAuth2Session` (sync, powered by `requests`) and `AsyncOAuth2Client` (async, powered by `httpx`). Both share the same API surface, making it easy to switch later. It also supports PKCE natively and has optional deep integrations for Flask, Django, and Starlette.

```python
from authlib.integrations.requests_client import OAuth2Session

client = OAuth2Session(client_id, client_secret, scope="accesslink.read_all")
uri, state = client.create_authorization_url("https://flow.polar.com/oauth2/authorization")

# After redirect back:
token = client.fetch_token(
    "https://polarremote.com/v2/oauth2/token",
    authorization_response=callback_url
)
```

**Assessment:** Slightly more powerful than `requests-oauthlib`, with better async story if needed later. Marginally heavier. The framework integrations are optional and can be entirely ignored — it works standalone.

### 1.5 Manual (`requests` only)

Using bare `requests` with Basic Auth for the token exchange. Works, but re-implements logic that the libraries above provide for free (state parameter, URL construction, error handling).

**Assessment:** Only justified if minimizing dependencies is a hard requirement. Not recommended.

### 1.6 Decision

For this project:

> **Use `requests-oauthlib`** for the one-time OAuth setup script.
> **Use `authlib`** if async API calls become relevant later (easy migration since APIs are similar).

Both are fully framework-agnostic. The OAuth module will be a standalone Python script with zero Streamlit dependency.

---

## 2. Recommended OAuth Implementation

### Design Principles

- The OAuth flow lives in **one isolated module**: `auth/polar_auth.py`
- It has **no imports from Streamlit**, no imports from the data layer
- It produces exactly one artifact: a token stored in `config.yml`
- It is run **once from the command line**, then never touched again
- The rest of the app only ever calls `auth.get_token()` → returns a string

### Module: `auth/polar_auth.py`

```python
"""
polar_auth.py
─────────────
Standalone OAuth2 authorization flow for the Polar AccessLink API.
Run once from CLI: python -m auth.polar_auth

Produces: config.yml with access_token and user_id written.
Has zero dependencies on Streamlit or any other app layer.
"""

import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

import yaml
from requests_oauthlib import OAuth2Session

# ── Polar OAuth2 endpoints ───────────────────────────────────────────────────
AUTH_URL   = "https://flow.polar.com/oauth2/authorization"
TOKEN_URL  = "https://polarremote.com/v2/oauth2/token"
REGISTER_URL = "https://www.polaraccesslink.com/v3/users"
REDIRECT_URI = "http://localhost:5000/callback"
SCOPE        = "accesslink.read_all"

CONFIG_PATH = "config.yml"


def load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def save_token(token: dict, user_id: str) -> None:
    config = load_config()
    config["access_token"] = token["access_token"]
    config["user_id"]      = user_id
    with open(CONFIG_PATH, "w") as f:
        yaml.dump(config, f)


def get_token() -> str:
    """Public interface: returns the stored access token. No OAuth logic here."""
    config = load_config()
    token = config.get("access_token")
    if not token:
        raise RuntimeError("No access token found. Run: python -m auth.polar_auth")
    return token


def _run_callback_server() -> str:
    """Start a local HTTP server, capture the OAuth callback code, return it."""
    code_holder = {}

    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            params = parse_qs(urlparse(self.path).query)
            code_holder["code"] = params.get("code", [None])[0]
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Authorization complete. You may close this tab.")

        def log_message(self, *args):
            pass  # suppress server logs

    server = HTTPServer(("localhost", 5000), CallbackHandler)
    server.handle_request()  # handle exactly one request, then stop
    return code_holder["code"]


def authorize() -> None:
    """Run the full one-time authorization flow."""
    config = load_config()
    client_id     = config["client_id"]
    client_secret = config["client_secret"]

    import requests

    oauth = OAuth2Session(client_id, redirect_uri=REDIRECT_URI, scope=SCOPE)
    auth_url, _ = oauth.authorization_url(AUTH_URL)

    print(f"\nOpening browser for Polar authorization...\n{auth_url}\n")
    webbrowser.open(auth_url)

    # Wait for callback
    code = _run_callback_server()
    if not code:
        raise RuntimeError("Authorization failed: no code received.")

    # Exchange code for token (Basic Auth as required by Polar)
    token = oauth.fetch_token(
        TOKEN_URL,
        code=code,
        client_secret=client_secret,
        include_client_id=True
    )

    # Register user (required once)
    user_id = token.get("x_user_id")
    requests.post(
        REGISTER_URL,
        headers={"Authorization": f"Bearer {token['access_token']}",
                 "Content-Type": "application/json"}
    )

    save_token(token, str(user_id))
    print(f"✓ Authorization complete. Token saved for user {user_id}.")


if __name__ == "__main__":
    authorize()
```

**Key properties of this design:**
- Single responsibility: auth only
- No framework import (no Flask, no Streamlit)
- `get_token()` is the only function the rest of the app ever calls
- Can be replaced entirely (e.g. by a Streamlit-based flow later) without touching any other layer

---

## 3. Layered Architecture: Separation of Concerns

The app is split into **five independent layers**. Each layer communicates with its neighbors only through defined interfaces (function signatures / return types). No layer imports from a layer above it.

```
┌─────────────────────────────────────────────────────────────────┐
│  Layer 5 — PRESENTATION                                         │
│  Streamlit pages: render charts, handle user interaction        │
│  Input:  figures (Plotly/Altair objects)                        │
│  Output: nothing (side effects only: display)                   │
└─────────────────────────┬───────────────────────────────────────┘
                          │ Plotly Figure / Altair Chart objects
┌─────────────────────────▼───────────────────────────────────────┐
│  Layer 4 — VISUALISATION                                        │
│  viz/charts.py: pure functions (DataFrame → Figure)            │
│  No Streamlit import. Testable standalone.                      │
└─────────────────────────┬───────────────────────────────────────┘
                          │ pd.DataFrame (clean, typed)
┌─────────────────────────▼───────────────────────────────────────┐
│  Layer 3 — ANALYSIS                                             │
│  analysis/hrv.py, analysis/sleep.py, analysis/training.py      │
│  Pure functions (DataFrame → DataFrame): rolling averages,      │
│  correlations, zone breakdowns. No I/O. Fully unit-testable.   │
└─────────────────────────┬───────────────────────────────────────┘
                          │ pd.DataFrame (raw, normalized)
┌─────────────────────────▼───────────────────────────────────────┐
│  Layer 2 — DATA (fetch + cache)                                 │
│  data/fetcher.py: calls Polar API → raw dict/JSON               │
│  data/transformer.py: raw dict → normalized pd.DataFrame        │
│  data/cache.py: Parquet read/write + @st.cache_data            │
└─────────────────────────┬───────────────────────────────────────┘
                          │ access_token (str)
┌─────────────────────────▼───────────────────────────────────────┐
│  Layer 1 — AUTH                                                 │
│  auth/polar_auth.py: OAuth2 flow (run once, CLI only)          │
│  Public interface: get_token() → str                            │
│  Zero imports from any other layer.                             │
└─────────────────────────────────────────────────────────────────┘
```

### Dependency Rules

| Layer | May import from | Must NOT import from |
|---|---|---|
| Presentation (5) | Viz (4), Analysis (3), Data (2), Auth (1) | — |
| Visualisation (4) | — (only `plotly`, `altair`, `pandas`) | Presentation, Auth |
| Analysis (3) | — (only `pandas`, `numpy`, `scipy`) | Presentation, Viz, Auth |
| Data (2) | Auth (1) only | Presentation, Viz, Analysis |
| Auth (1) | — (only `requests-oauthlib`, `yaml`) | All other layers |

This means: **Layers 3 and 4 are completely pure Python with no app dependencies.** They can be unit-tested, reused in a different UI framework, or called from a Jupyter notebook without any changes.

---

## 4. Layer Specifications

### Layer 1 — Auth (`auth/`)

```
auth/
  polar_auth.py     ← OAuth flow + get_token() interface
  __init__.py       ← exports: get_token
```

**Public API:**
```python
from auth import get_token
token: str = get_token()   # raises RuntimeError if not authorized
```

---

### Layer 2 — Data (`data/`)

```
data/
  fetcher.py        ← HTTP calls to Polar API → raw dicts
  transformer.py    ← raw dict → normalized pd.DataFrame
  cache.py          ← Parquet persistence + @st.cache_data wrappers
  __init__.py       ← exports: get_nightly_recharge, get_sleep, get_exercises
```

**`fetcher.py` — raw API calls, returns dicts:**
```python
import requests

BASE_URL = "https://www.polaraccesslink.com/v3"

def fetch_nightly_recharge(token: str, since: str, until: str) -> list[dict]:
    """Returns raw API response as list of dicts. No transformation."""
    resp = requests.get(
        f"{BASE_URL}/users/recharge",
        headers={"Authorization": f"Bearer {token}"},
        params={"from": since, "to": until}
    )
    resp.raise_for_status()
    return resp.json().get("recharge", [])
```

**`transformer.py` — pure transformation, no I/O:**
```python
import pandas as pd

def nightly_recharge_to_df(raw: list[dict]) -> pd.DataFrame:
    """
    Maps raw API response to a clean, typed DataFrame.
    Columns: date, hrv_avg_ms, ans_charge, hr_avg, breathing_rate,
             sleep_charge, recharge_status
    """
    records = [
        {
            "date":            pd.to_datetime(r["date"]),
            "hrv_avg_ms":      r.get("heart_rate_variability_avg"),
            "ans_charge":      r.get("ans_charge"),
            "hr_avg":          r.get("heart_rate_avg"),
            "breathing_rate":  r.get("breathing_rate"),
            "sleep_charge":    r.get("sleep_charge"),
            "recharge_status": r.get("nightly_recharge_status"),
        }
        for r in raw
    ]
    return pd.DataFrame(records).sort_values("date").reset_index(drop=True)
```

**`cache.py` — persistence + session cache:**
```python
import streamlit as st
import pandas as pd
from pathlib import Path
from auth import get_token
from data.fetcher import fetch_nightly_recharge
from data.transformer import nightly_recharge_to_df

CACHE_DIR = Path("cache")
CACHE_DIR.mkdir(exist_ok=True)

@st.cache_data(ttl=3600)
def get_nightly_recharge() -> pd.DataFrame:
    path = CACHE_DIR / "nightly_recharge.parquet"

    # Load from disk if available
    df = pd.read_parquet(path) if path.exists() else pd.DataFrame()

    # Fetch only new data
    since = str(df["date"].max().date()) if not df.empty else "2020-01-01"
    until = str(pd.Timestamp.today().date())

    raw = fetch_nightly_recharge(get_token(), since=since, until=until)
    if raw:
        new_df = nightly_recharge_to_df(raw)
        df = pd.concat([df, new_df]).drop_duplicates("date").sort_values("date")
        df.to_parquet(path, index=False)

    return df
```

---

### Layer 3 — Analysis (`analysis/`)

```
analysis/
  hrv.py         ← rolling averages, trends, anomaly flags
  sleep.py       ← stage ratios, efficiency, score trends
  training.py    ← load, zone distribution, volume over time
  __init__.py
```

**Pure functions only. No I/O. No Streamlit. No API calls.**

```python
# analysis/hrv.py

import pandas as pd
import numpy as np

def add_rolling_average(df: pd.DataFrame, column: str, window: int = 7) -> pd.DataFrame:
    """Add a rolling mean column. Returns a copy."""
    df = df.copy()
    df[f"{column}_rolling{window}"] = df[column].rolling(window, min_periods=1).mean()
    return df

def flag_low_hrv(df: pd.DataFrame, threshold_percentile: int = 20) -> pd.DataFrame:
    """Flag rows where HRV is below the given percentile as 'low_recovery'."""
    df = df.copy()
    cutoff = df["hrv_avg_ms"].quantile(threshold_percentile / 100)
    df["low_recovery"] = df["hrv_avg_ms"] < cutoff
    return df

def correlate_hrv_with_training_load(
    hrv_df: pd.DataFrame,
    training_df: pd.DataFrame,
    lag_days: int = 1
) -> pd.DataFrame:
    """
    Shift training load by lag_days, merge with HRV, return correlation DataFrame.
    """
    load = training_df[["date", "load"]].copy()
    load["date"] = load["date"] + pd.Timedelta(days=lag_days)
    merged = hrv_df.merge(load, on="date", how="inner")
    return merged[["date", "hrv_avg_ms", "load"]]
```

---

### Layer 4 — Visualisation (`viz/`)

```
viz/
  charts_hrv.py       ← HRV time series charts
  charts_sleep.py     ← Sleep stage charts
  charts_training.py  ← Training load, HR zone charts
  theme.py            ← shared color palette, layout defaults
  __init__.py
```

**Pure functions: `pd.DataFrame → plotly.graph_objects.Figure`**
**No Streamlit import. No data fetching.**

```python
# viz/charts_hrv.py

import plotly.graph_objects as go
import pandas as pd
from viz.theme import COLORS, LAYOUT_DEFAULTS

def hrv_timeseries(df: pd.DataFrame) -> go.Figure:
    """
    Renders daily HRV avg with 7-day rolling average overlay.
    Input: DataFrame with columns [date, hrv_avg_ms, hrv_avg_ms_rolling7]
    """
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df["date"], y=df["hrv_avg_ms"],
        mode="markers+lines",
        name="HRV avg (daily)",
        line=dict(color=COLORS["hrv"], width=1),
        opacity=0.5
    ))

    if "hrv_avg_ms_rolling7" in df.columns:
        fig.add_trace(go.Scatter(
            x=df["date"], y=df["hrv_avg_ms_rolling7"],
            mode="lines",
            name="7-day average",
            line=dict(color=COLORS["hrv"], width=2.5)
        ))

    fig.update_layout(
        **LAYOUT_DEFAULTS,
        title="Nightly HRV",
        xaxis_title="Date",
        yaxis_title="HRV (ms)"
    )
    return fig
```

---

### Layer 5 — Presentation (`pages/`)

The only layer that imports Streamlit. Assembles data, analysis, and charts; handles user input (date pickers, refresh buttons).

```python
# pages/1_HRV_Recharge.py

import streamlit as st
from data import get_nightly_recharge
from analysis.hrv import add_rolling_average, flag_low_hrv
from viz.charts_hrv import hrv_timeseries

st.title("HRV & Nightly Recharge")

# — Data —
df = get_nightly_recharge()

# — Analysis —
df = add_rolling_average(df, "hrv_avg_ms", window=7)
df = flag_low_hrv(df)

# — Presentation —
col1, col2 = st.columns(2)
with col1:
    days = st.slider("Show last N days", 30, 365, 90)
with col2:
    if st.button("🔄 Refresh data"):
        st.cache_data.clear()
        st.rerun()

filtered = df.tail(days)
st.plotly_chart(hrv_timeseries(filtered), use_container_width=True)
```

---

## 5. Interface Contracts Between Layers

A summary of exactly what flows between layers — this is the contract each layer must honour.

```
Auth     →  Data:        access_token: str
Data     →  Analysis:    pd.DataFrame (normalized, typed columns, date sorted)
Analysis →  Viz:         pd.DataFrame (same schema + computed columns added)
Viz      →  Presentation: plotly.graph_objects.Figure | altair.Chart
```

### Normalized DataFrame Schemas

**Nightly Recharge:**
```
date              datetime64[ns]   — primary key
hrv_avg_ms        float64
ans_charge        float64
hr_avg            float64
breathing_rate    float64
sleep_charge      float64
recharge_status   str              — "very_poor" | "poor" | "compromised" |
                                     "sustained" | "very_good"
```

**Sleep:**
```
date              datetime64[ns]
sleep_score       float64
sleep_start       datetime64[ns]
sleep_end         datetime64[ns]
total_minutes     float64
deep_minutes      float64
light_minutes     float64
rem_minutes       float64
interruptions     int64
```

**Exercises:**
```
exercise_id       str              — unique, immutable (transactional!)
date              datetime64[ns]
sport             str
duration_min      float64
calories          float64
hr_avg            float64
hr_max            float64
zone1_min ... zone5_min  float64  — HR zone durations
```

---

## 6. Final Project Structure

```
polar-dashboard/
│
├── app.py                     # Streamlit entry: st.set_page_config + sidebar
├── config.yml                 # Credentials (gitignored)
├── requirements.txt
├── .gitignore
│
├── auth/                      # Layer 1 — Auth
│   ├── __init__.py            # exports: get_token
│   └── polar_auth.py          # OAuth2 flow (CLI) + get_token()
│
├── data/                      # Layer 2 — Data
│   ├── __init__.py            # exports: get_nightly_recharge, get_sleep, get_exercises
│   ├── fetcher.py             # Raw HTTP calls → dict
│   ├── transformer.py         # dict → pd.DataFrame (normalized schema)
│   └── cache.py               # Parquet + @st.cache_data wrappers
│
├── analysis/                  # Layer 3 — Analysis
│   ├── __init__.py
│   ├── hrv.py                 # rolling avg, recovery flags, correlations
│   ├── sleep.py               # stage ratios, efficiency metrics
│   └── training.py            # load, volume, zone distribution
│
├── viz/                       # Layer 4 — Visualisation
│   ├── __init__.py
│   ├── theme.py               # colors, layout defaults
│   ├── charts_hrv.py          # DataFrame → Plotly Figure
│   ├── charts_sleep.py
│   └── charts_training.py
│
├── pages/                     # Layer 5 — Presentation (Streamlit)
│   ├── 1_HRV_Recharge.py
│   ├── 2_Sleep.py
│   ├── 3_Training.py
│   └── 4_Correlations.py
│
├── cache/                     # Runtime Parquet files (gitignored)
│   ├── nightly_recharge.parquet
│   ├── sleep.parquet
│   └── exercises.parquet
│
└── tests/                     # Unit tests (Layers 3+4 are trivially testable)
    ├── test_analysis_hrv.py
    ├── test_transformer.py
    └── test_charts_hrv.py     # assert fig.data is not empty etc.
```

### What this architecture enables

| Scenario | How the architecture supports it |
|---|---|
| **Switch from Streamlit to Next.js** | Replace `pages/` only. Layers 1–4 unchanged. |
| **Add a new data source** (Garmin, Oura) | Add `data/fetcher_oura.py` + `data/transformer_oura.py`. Analysis + viz layers untouched. |
| **Run analysis in Jupyter** | `from analysis.hrv import add_rolling_average` — works without Streamlit installed. |
| **Unit test analysis logic** | Pure functions with no I/O, trivially testable with `pytest`. |
| **Add multi-user OAuth** | Replace `auth/polar_auth.py` only. Token storage logic isolated there. |
| **Switch chart library** (Plotly → ECharts) | Replace `viz/` only. Analysis DataFrames stay identical. |
