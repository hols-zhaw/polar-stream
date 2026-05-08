# Setup Guide

## Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (fast Python package installer)

## Initial Setup

### 1. Create Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate  # On macOS/Linux
# or
.venv\Scripts\activate  # On Windows
```

### 2. Install uv (if not already installed)

```bash
pip install uv
```

### 3. Generate Locked Dependencies

```bash
uv pip compile requirements.in -o requirements.txt
```

### 4. Install Dependencies

```bash
uv pip install -r requirements.txt
```

## Configure Polar API Access

### 1. Create Configuration File

```bash
cp config.example.yml config.yml
```

### 2. Register Your App

1. Go to [Polar AccessLink](https://admin.polaraccesslink.com/)
2. Create a new client application
3. Copy `client_id` and `client_secret` to `config.yml`

### 3. Authorize Access

```bash
python -m auth.polar_auth
```

This will:
- Open your browser for OAuth authorization
- Save your access token to `config.yml`
- Register you as a user with the Polar API

## Run the Dashboard

```bash
streamlit run app.py
```

The dashboard will open at `http://localhost:8501`.

## Project Structure

```
polar-stream/
├── auth/           # Layer 1: OAuth2 authentication
├── data/           # Layer 2: API data fetching and caching
├── analysis/       # Layer 3: Pure data transformations
├── viz/            # Layer 4: Pure chart generation
├── pages/          # Layer 5: Streamlit presentation
├── tests/          # Validation tests
├── cache/          # Parquet cache (gitignored, local only)
├── config.yml      # API credentials (gitignored)
└── app.py          # Main entry point
```

## Development

### Run Tests

```bash
python3 tests/test_layer_isolation.py
```

### Update Dependencies

Edit `requirements.in`, then regenerate:

```bash
uv pip compile requirements.in -o requirements.txt
uv pip install -r requirements.txt
```

## Deployment

For Streamlit Cloud deployment:
- Data is cached in `st.session_state` (per-user isolation)
- Parquet caching is disabled (ephemeral filesystem)
- Configure secrets in Streamlit Cloud settings UI
