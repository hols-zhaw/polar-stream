"""
transformer.py
──────────────
Layer 2 — Data Transformer
Pure transformations: raw API dicts → normalized pd.DataFrame.

No I/O, no API calls—just data shaping and type conversion.
All functions are pure: same input always produces same output.
"""

import pandas as pd
from typing import Optional
import re


def nightly_recharge_to_df(raw: list[dict]) -> pd.DataFrame:
    """
    Transform raw Polar nightly recharge API response to clean DataFrame.
    
    Args:
        raw: List of raw nightly recharge records from API
        
    Returns:
        DataFrame with schema:
            date: datetime64[ns] — primary key
            hrv_avg_ms: float64
            ans_charge: float64
            hr_avg: float64
            breathing_rate: float64
            sleep_charge: float64
            recharge_status: str — "very_poor"|"poor"|"compromised"|"sustained"|"very_good"
    """
    if not raw:
        return pd.DataFrame()
    
    # Map status codes to readable strings
    STATUS_MAP = {
        1: "very_poor",
        2: "poor",
        3: "compromised",
        4: "sustained",
        5: "very_good",
    }
    
    records = [
        {
            "date": pd.to_datetime(r["date"]),
            "hrv_avg_ms": float(r.get("heart_rate_variability_avg", 0)) if r.get("heart_rate_variability_avg") else None,
            "ans_charge": float(r.get("ans_charge", 0)) if r.get("ans_charge") else None,
            "hr_avg": float(r.get("heart_rate_avg", 0)) if r.get("heart_rate_avg") else None,
            "breathing_rate": float(r.get("breathing_rate_avg", 0)) if r.get("breathing_rate_avg") else None,
            "sleep_charge": float(r.get("sleep_charge", 0)) if r.get("sleep_charge") else None,
            "recharge_status": STATUS_MAP.get(r.get("nightly_recharge_status"), "unknown"),
        }
        for r in raw
    ]
    
    df = pd.DataFrame(records)
    return df.sort_values("date").reset_index(drop=True)


def sleep_to_df(raw: list[dict]) -> pd.DataFrame:
    """
    Transform raw Polar sleep API response to clean DataFrame.
    
    Args:
        raw: List of raw sleep records from API
        
    Returns:
        DataFrame with schema:
            date: datetime64[ns] — primary key  
            sleep_score: float64
            sleep_start: datetime64[ns]
            sleep_end: datetime64[ns]
            total_minutes: float64
            deep_minutes: float64
            light_minutes: float64
            rem_minutes: float64
            interruptions: int64
    """
    if not raw:
        return pd.DataFrame()
    
    records = [
        {
            "date": pd.to_datetime(r["date"]),
            "sleep_score": float(r.get("sleep_score", 0)) if r.get("sleep_score") else None,
            "sleep_start": pd.to_datetime(r.get("sleep_start_time")) if r.get("sleep_start_time") else None,
            "sleep_end": pd.to_datetime(r.get("sleep_end_time")) if r.get("sleep_end_time") else None,
            "total_minutes": (
                (float(r.get("light_sleep", 0)) + float(r.get("deep_sleep", 0)) + float(r.get("rem_sleep", 0))) / 60
                if r.get("light_sleep") is not None else None
            ),
            "deep_minutes": float(r.get("deep_sleep", 0)) / 60 if r.get("deep_sleep") is not None else None,
            "light_minutes": float(r.get("light_sleep", 0)) / 60 if r.get("light_sleep") is not None else None,
            "rem_minutes": float(r.get("rem_sleep", 0)) / 60 if r.get("rem_sleep") is not None else None,
            "interruptions": int(r.get("short_interruption", 0) + r.get("long_interruption", 0)),
        }
        for r in raw
    ]
    
    df = pd.DataFrame(records)
    return df.sort_values("date").reset_index(drop=True)


def _parse_duration_to_minutes(duration_str: Optional[str]) -> Optional[float]:
    """
    Parse ISO 8601 duration string to minutes.
    Example: "PT1H30M15S" → 90.25
    """
    if not duration_str:
        return None
    
    pattern = r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?'
    match = re.match(pattern, duration_str)
    if not match:
        return None
    
    hours = int(match.group(1)) if match.group(1) else 0
    minutes = int(match.group(2)) if match.group(2) else 0
    seconds = int(match.group(3)) if match.group(3) else 0
    
    return hours * 60 + minutes + seconds / 60


def exercise_to_df(raw: list[dict]) -> pd.DataFrame:
    """
    Transform raw Polar exercise API response to clean DataFrame.
    
    Args:
        raw: List of raw exercise records from API (transactional data)
        
    Returns:
        DataFrame with schema:
            exercise_id: str — unique, immutable (primary key)
            date: datetime64[ns]
            sport: str
            duration_min: float64
            calories: float64
            hr_avg: float64
            hr_max: float64
            distance_km: float64
            training_load: float64
    """
    if not raw:
        return pd.DataFrame()
    
    records = [
        {
            "exercise_id": str(r.get("id")),
            "date": pd.to_datetime(r.get("start_time")),
            "sport": r.get("detailed_sport_info", r.get("sport", "unknown")),
            "duration_min": _parse_duration_to_minutes(r.get("duration")),
            "calories": float(r.get("calories", 0)) if r.get("calories") else None,
            "hr_avg": float(r.get("heart_rate", {}).get("average", 0)) if r.get("heart_rate", {}).get("average") else None,
            "hr_max": float(r.get("heart_rate", {}).get("maximum", 0)) if r.get("heart_rate", {}).get("maximum") else None,
            "distance_km": float(r.get("distance", 0)) / 1000 if r.get("distance") else None,
            "training_load": float(r.get("training_load", 0)) if r.get("training_load") else None,
        }
        for r in raw
    ]
    
    df = pd.DataFrame(records)
    return df.sort_values("date").reset_index(drop=True)
