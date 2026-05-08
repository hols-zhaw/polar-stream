"""
cache.py
────────
Layer 2 — Data Cache
Pure Parquet persistence with environment-aware behavior.

Local dev: Incremental fetch + Parquet cache (fast, survives restarts)
Cloud: Fresh API fetch (no persistent storage, per-session only in Layer 5)

NO Streamlit imports—this layer is framework-agnostic.
"""

import os
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta

from auth import get_token
from data.fetcher import (
    fetch_nightly_recharge,
    fetch_sleep,
    fetch_available_exercises,
    fetch_exercise,
)
from data.transformer import (
    nightly_recharge_to_df,
    sleep_to_df,
    exercise_to_df,
)

# ── Configuration ─────────────────────────────────────────────────────────────
CACHE_DIR = Path("cache")
IS_LOCAL = not os.getenv("STREAMLIT_SHARING")  # Detect Streamlit Cloud vs local

# Create cache directory only in local development
if IS_LOCAL:
    CACHE_DIR.mkdir(exist_ok=True)


def load_nightly_recharge() -> pd.DataFrame:
    """
    Load nightly recharge data from Parquet (local) or fresh API fetch (cloud).
    Pure function: no Streamlit dependencies.
    
    Local: Incremental fetch with Parquet cache (fast, survives restarts)
    Cloud: Full fetch from API (no persistent storage, per-session only)
    
    Returns:
        DataFrame with nightly recharge data, sorted by date
    """
    cache_file = CACHE_DIR / "nightly_recharge.parquet"
    
    # Local: load existing cache and fetch only new data
    if IS_LOCAL and cache_file.exists():
        df = pd.read_parquet(cache_file)
        since = str(df["date"].max().date() + timedelta(days=1))  # Day after last cached
        print(f"📦 Loaded {len(df)} cached nightly recharge records")
    else:
        df = pd.DataFrame()
        since = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")  # Last 90 days
        print(f"🌐 Fetching nightly recharge data from {since}")
    
    until = datetime.now().strftime("%Y-%m-%d")
    
    try:
        raw = fetch_nightly_recharge(get_token(), since=since, until=until)
        
        if raw:
            new_df = nightly_recharge_to_df(raw)
            print(f"✓ Fetched {len(new_df)} new nightly recharge records")
            df = pd.concat([df, new_df]).drop_duplicates("date").sort_values("date")
            
            # Persist to Parquet only in local dev (not in cloud)
            if IS_LOCAL:
                df.to_parquet(cache_file, index=False)
                print(f"💾 Saved to {cache_file}")
        else:
            print("No new nightly recharge data")
    
    except Exception as e:
        print(f"⚠️  Error fetching nightly recharge: {e}")
        if df.empty:
            raise
    
    return df.reset_index(drop=True)


def load_sleep() -> pd.DataFrame:
    """
    Load sleep data from Parquet (local) or fresh API fetch (cloud).
    
    Returns:
        DataFrame with sleep data, sorted by date
    """
    cache_file = CACHE_DIR / "sleep.parquet"
    
    if IS_LOCAL and cache_file.exists():
        df = pd.read_parquet(cache_file)
        since = str(df["date"].max().date() + timedelta(days=1))
        print(f"📦 Loaded {len(df)} cached sleep records")
    else:
        df = pd.DataFrame()
        since = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
        print(f"🌐 Fetching sleep data from {since}")
    
    until = datetime.now().strftime("%Y-%m-%d")
    
    try:
        raw = fetch_sleep(get_token(), since=since, until=until)
        
        if raw:
            new_df = sleep_to_df(raw)
            print(f"✓ Fetched {len(new_df)} new sleep records")
            df = pd.concat([df, new_df]).drop_duplicates("date").sort_values("date")
            
            if IS_LOCAL:
                df.to_parquet(cache_file, index=False)
                print(f"💾 Saved to {cache_file}")
        else:
            print("No new sleep data")
    
    except Exception as e:
        print(f"⚠️  Error fetching sleep: {e}")
        if df.empty:
            raise
    
    return df.reset_index(drop=True)


def load_exercises() -> pd.DataFrame:
    """
    Load exercise data with TRANSACTIONAL awareness.
    
    CRITICAL: Polar exercises are transactional—each can only be fetched ONCE.
    After retrieval, the data is deleted from the API.
    
    Strategy:
    - Local: Load from Parquet + fetch new transactions
    - Cloud: Load from Parquet if exists, otherwise fetch all available
    
    Returns:
        DataFrame with exercise data, sorted by date
    """
    cache_file = CACHE_DIR / "exercises.parquet"
    
    # Always try to load existing cache first (critical for transactional data)
    if cache_file.exists():
        df = pd.read_parquet(cache_file)
        print(f"📦 Loaded {len(df)} cached exercise records")
    else:
        df = pd.DataFrame()
        print("No existing exercise cache")
    
    try:
        # Fetch available exercise transactions
        transaction_urls = fetch_available_exercises(get_token())
        
        if transaction_urls:
            print(f"🔗 Found {len(transaction_urls)} new exercise transactions")
            
            # Fetch each transaction (WARNING: one-time only!)
            new_exercises = []
            for url in transaction_urls:
                try:
                    exercise_data = fetch_exercise(get_token(), url)
                    new_exercises.append(exercise_data)
                except Exception as e:
                    print(f"⚠️  Failed to fetch exercise from {url}: {e}")
            
            if new_exercises:
                new_df = exercise_to_df(new_exercises)
                print(f"✓ Fetched {len(new_df)} new exercises")
                df = pd.concat([df, new_df]).drop_duplicates("exercise_id").sort_values("date")
                
                # ALWAYS persist exercises immediately (transactional data!)
                df.to_parquet(cache_file, index=False)
                print(f"💾 Saved to {cache_file} (transactional data preserved)")
        else:
            print("No new exercise transactions available")
    
    except Exception as e:
        print(f"⚠️  Error fetching exercises: {e}")
        if df.empty:
            raise
    
    return df.reset_index(drop=True)
