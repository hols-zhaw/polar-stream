"""
fetcher.py
──────────
Layer 2 — Data Fetcher
Raw HTTP calls to Polar AccessLink API → returns dicts/lists.

No transformation, no caching—just fetch and return.
Pure functions with explicit dependencies (token passed as argument).
"""

import requests
from typing import Optional

# Polar AccessLink API base URLs
BASE_URL_V3 = "https://www.polaraccesslink.com/v3"


def fetch_user_info(token: str, user_id: str) -> dict:
    """
    Fetch user information from Polar API.

    Args:
        token: Polar API access token
        user_id: Polar user ID

    Returns:
        User info dict with keys:
        - polar-user-id: int
        - member-id: str
        - registration-date: str
        - first-name: str
        - last-name: str
        - birthdate: str
        - gender: str
        - weight: float (kg)
        - height: float (cm)
    """
    resp = requests.get(
        f"{BASE_URL_V3}/users/{user_id}",
        headers={"Accept": "application/json", "Authorization": f"Bearer {token}"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def fetch_nightly_recharge(token: str, since: str, until: str) -> list[dict]:
    """
    Fetch nightly recharge data from Polar API.

    Args:
        token: Polar API access token
        since: Start date (ISO format: YYYY-MM-DD)
        until: End date (ISO format: YYYY-MM-DD)

    Returns:
        List of raw nightly recharge records (dicts)

    API Response Schema (per record):
        - date: str (YYYY-MM-DD)
        - polar_user: str
        - heart_rate_avg: int
        - heart_rate_variability_avg: int (ms)
        - breathing_rate_avg: float
        - nightly_recharge_status: int
        - ans_charge: float
        - ans_charge_status: int
        - hrv_samples: dict
        - sleep_charge: float
        - sleep_charge_status: int
        - sleep_score: int
    """
    resp = requests.get(
        f"{BASE_URL_V3}/users/nightly-recharge",
        headers={"Authorization": f"Bearer {token}"},
        params={"date": since},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()

    # API returns {"recharges": [...]}
    return data.get("recharges", [])


def fetch_sleep(token: str, since: str, until: str) -> list[dict]:
    """
    Fetch sleep data from Polar API.

    Args:
        token: Polar API access token
        since: Start date (ISO format: YYYY-MM-DD)
        until: End date (ISO format: YYYY-MM-DD)

    Returns:
        List of raw sleep records (dicts)

    API Response Schema (per record):
        - polar_user: str
        - date: str (YYYY-MM-DD)
        - sleep_start_time: str (ISO datetime)
        - sleep_end_time: str (ISO datetime)
        - device_id: str
        - continuity: float
        - continuity_class: int
        - light_sleep: int (seconds)
        - deep_sleep: int (seconds)
        - rem_sleep: int (seconds)
        - unrecognized_sleep_stage: int (seconds)
        - sleep_score: int
        - total_interruption_duration: int (seconds)
        - sleep_charge: float
        - sleep_goal: int (seconds)
        - sleep_rating: int
        - short_interruption: int (count)
        - long_interruption: int (count)
        - sleep_cycles: int
        - group_duration_score: float
        - group_solidity_score: float
        - group_regeneration_score: float
    """
    resp = requests.get(
        f"{BASE_URL_V3}/users/sleep",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()

    # API returns {"nights": [...]}
    return data.get("nights", [])


def fetch_available_exercises(token: str) -> list[str]:
    """
    Fetch list of available exercise transaction URLs.

    CRITICAL: Polar uses a transactional model for exercises.
    Each URL can only be fetched ONCE—it's deleted after retrieval.

    Args:
        token: Polar API access token

    Returns:
        List of exercise transaction URLs
    """
    resp = requests.get(
        f"{BASE_URL_V3}/exercises",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()

    # API might return list directly or {"exercises": [...]} or {"available-user-data": [...]}
    if isinstance(data, list):
        return data
    elif isinstance(data, dict):
        # Try common response formats
        return data.get("exercises", data.get("available-user-data", []))
    else:
        return []


def fetch_exercise(token: str, exercise_url: str) -> dict:
    """
    Fetch a single exercise by its transaction URL.

    WARNING: This URL can only be accessed ONCE. The data is deleted after fetch.
    Always persist the result immediately to prevent data loss.

    Args:
        token: Polar API access token
        exercise_url: Full exercise transaction URL

    Returns:
        Raw exercise record (dict)

    API Response Schema:
        - id: int
        - upload_time: str (ISO datetime)
        - polar_user: str
        - device: str
        - device_id: str
        - start_time: str (ISO datetime)
        - start_time_utc_offset: int (minutes)
        - duration: str (duration format: PT1H30M15S)
        - calories: int
        - distance: float (meters)
        - heart_rate: dict
        - training_load: float
        - sport: str
        - has_route: bool
        - club_id: int
        - club_name: str
        - detailed_sport_info: str
        - fat_percentage: int
        - carbohydrate_percentage: int
        - protein_percentage: int
        - running_index: int
        - training_load_pro: dict
    """
    resp = requests.get(
        exercise_url,
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()
