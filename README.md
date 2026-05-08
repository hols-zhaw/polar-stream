# Polar Stream

> Your Polar data, your dashboard — stream your training, recovery and sleep into custom analytics.

A personal analytics dashboard for [Polar](https://www.polar.com) sports watches, built with [Streamlit](https://streamlit.io) and the [Polar AccessLink API](https://www.polar.com/accesslink-api/). Visualizes nightly HRV trends, recovery scores, and sleep quality beyond what Polar Flow offers out of the box.

![Python](https://img.shields.io/badge/python-3.14+-blue) ![Streamlit](https://img.shields.io/badge/streamlit-1.x-red) ![License](https://img.shields.io/badge/license-MIT-green)

---

## Features

- 🫀 Nightly HRV, ANS charge and 7-day rolling trends
- 💤 Sleep stage trends and scores
- 🏃 Training load, HR zones and exercise history
- ⚡ Local Parquet cache — fast reloads, no redundant API calls

## Requirements

- Python 3.11+
- A [Polar Flow](https://flow.polar.com) account + compatible Polar device
- A registered [AccessLink API client](https://admin.polaraccesslink.com)

## Setup

Clone and install dependencies using [uv](https://github.com/astral-sh/uv):

```bash
git clone https://github.com/YOUR_USERNAME/polar-stream
cd polar-stream
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

> To regenerate the lockfile from `requirements.in`: `uv pip compile requirements.in -o requirements.txt`

Copy and fill in your credentials:

```bash
cp config.example.yml config.yml
# edit config.yml and add your client_id and client_secret
```

Run the one-time OAuth authorization (opens a browser window):

```bash
python -m auth.polar_auth
```

This saves an `access_token` and `user_id` to `config.yml`. You only need to do this once.

Launch the app:

```bash
streamlit run app.py
```

## Architecture

Strict 5-layer separation — each layer only imports from the layer below it:

```
Layer 5: pages/          Streamlit UI — wires everything together
Layer 4: viz/            Pure chart functions (DataFrame → Plotly Figure)
Layer 3: analysis/       Pure transformations (DataFrame → DataFrame)
Layer 2: data/           API fetcher, transformer, Parquet cache
Layer 1: auth/           OAuth2 flow, token storage
```

Data flows one way: `auth → data → analysis → viz → pages`. No layer reaches up.

## Project structure

```
auth/
  polar_auth.py       OAuth2 flow + get_token() / get_user_id()
data/
  fetcher.py          Raw HTTP calls to Polar AccessLink API
  transformer.py      API dicts → normalized DataFrames
  cache.py            Incremental Parquet cache (local) / fresh fetch (cloud)
analysis/
  hrv.py              HRV rolling averages, recovery scores, flagging
viz/
  theme.py            Color constants and shared Plotly layout defaults
  charts_hrv.py       HRV/recharge chart functions
pages/
  1_HRV_Recharge.py   HRV & Nightly Recharge dashboard
  2_Diagnostics.py    API connectivity diagnostics
tests/
  test_layer_isolation.py  Validates layer boundaries and pure functions
config.example.yml    Credential template (copy to config.yml)
requirements.in       Dependency source for uv pip compile
requirements.txt      Locked dependencies
```

## License

MIT

