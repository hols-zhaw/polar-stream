# Polar Stream

> Your Polar data, your dashboard — stream your training, recovery and sleep into custom analytics.

A personal analytics dashboard for [Polar](https://www.polar.com) sports watches, built with [Streamlit](https://streamlit.io) and the [Polar AccessLink API](https://www.polar.com/accesslink-api/). Visualizes nightly HRV trends, sleep quality, and training performance beyond what Polar Flow offers out of the box.

![Python](https://img.shields.io/badge/python-3.14+-blue) ![Streamlit](https://img.shields.io/badge/streamlit-1.x-red) ![License](https://img.shields.io/badge/license-MIT-green)

---

## Features

- 📈 Nightly HRV & ANS charge time series
- 😴 Sleep stage trends and scores
- 🏃 Training load, HR zones and exercise history
- ⚡ Local Parquet cache — fast reloads, no redundant API calls

## Requirements

- Python 3.11+
- A [Polar Flow](https://flow.polar.com) account + compatible Polar device
- A registered [AccessLink API client](https://admin.polaraccesslink.com)

## Setup

```bash
git clone https://github.com/YOUR_USERNAME/polar-stream
cd polar-stream
pip install -r requirements.txt
```

Copy and fill in your credentials:

```bash
cp config.example.yml config.yml
# add your client_id and client_secret
```

Run the one-time OAuth authorization:

```bash
python -m auth.polar_auth
```

Launch the app:

```bash
streamlit run app.py
```

## Project structure

```
auth/          OAuth2 flow (run once)
data/          API fetcher, transformer, Parquet cache
analysis/      Pure analysis functions (HRV, sleep, training)
viz/           Chart functions (Plotly)
pages/         Streamlit pages
```

## License

MIT
