"""
hrv.py
──────
Layer 3 — HRV Analysis
Pure DataFrame transformations for heart rate variability analysis.

All functions are pure: DataFrame in → DataFrame out, no side effects.
No I/O, no API calls, no Streamlit—fully unit-testable in isolation.
"""

import pandas as pd
import numpy as np


def add_rolling_average(
    df: pd.DataFrame, column: str, window: int = 7
) -> pd.DataFrame:
    """
    Add rolling average column to DataFrame.
    
    Args:
        df: Input DataFrame with time series data
        column: Column name to calculate rolling average for
        window: Rolling window size in days (default: 7)
        
    Returns:
        DataFrame copy with new column: {column}_rolling{window}
        
    Example:
        >>> df = add_rolling_average(df, "hrv_avg_ms", window=7)
        >>> "hrv_avg_ms_rolling7" in df.columns
        True
    """
    df = df.copy()
    df[f"{column}_rolling{window}"] = (
        df[column].rolling(window, min_periods=1).mean()
    )
    return df


def flag_low_hrv(
    df: pd.DataFrame, threshold_percentile: int = 20
) -> pd.DataFrame:
    """
    Flag rows where HRV is below the given percentile as low recovery.
    
    Args:
        df: DataFrame with hrv_avg_ms column
        threshold_percentile: Percentile threshold (0-100, default: 20)
        
    Returns:
        DataFrame copy with new boolean column: low_recovery
        
    Example:
        >>> df = flag_low_hrv(df, threshold_percentile=20)
        >>> df[df["low_recovery"]].shape[0]  # Count of low HRV days
    """
    if "hrv_avg_ms" not in df.columns:
        raise ValueError("DataFrame must contain 'hrv_avg_ms' column")
    
    df = df.copy()
    cutoff = df["hrv_avg_ms"].quantile(threshold_percentile / 100)
    df["low_recovery"] = df["hrv_avg_ms"] < cutoff
    return df


def calculate_hrv_trend(df: pd.DataFrame, window: int = 30) -> pd.DataFrame:
    """
    Calculate HRV trend direction over a sliding window.
    
    Args:
        df: DataFrame with date and hrv_avg_ms columns (sorted by date)
        window: Sliding window size in days (default: 30)
        
    Returns:
        DataFrame copy with new column: hrv_trend (slope of linear fit)
        Positive values indicate improving HRV, negative = declining.
    """
    if "hrv_avg_ms" not in df.columns or "date" not in df.columns:
        raise ValueError("DataFrame must contain 'date' and 'hrv_avg_ms' columns")
    
    df = df.copy().sort_values("date")
    
    def linear_trend(series):
        """Fit linear regression, return slope."""
        if len(series) < 2:
            return 0.0
        x = np.arange(len(series))
        y = series.values
        # Filter out NaN values
        mask = ~np.isnan(y)
        if mask.sum() < 2:
            return 0.0
        slope, _ = np.polyfit(x[mask], y[mask], 1)
        return slope
    
    df["hrv_trend"] = (
        df["hrv_avg_ms"]
        .rolling(window, min_periods=7)
        .apply(linear_trend, raw=False)
    )
    
    return df


def correlate_hrv_with_metric(
    hrv_df: pd.DataFrame,
    metric_df: pd.DataFrame,
    metric_column: str,
    lag_days: int = 1,
) -> pd.DataFrame:
    """
    Correlate HRV with another metric (e.g., training load, sleep score).
    Applies a lag to the metric to analyze delayed effects.
    
    Args:
        hrv_df: DataFrame with date and hrv_avg_ms columns
        metric_df: DataFrame with date and the metric column
        metric_column: Name of the metric column to correlate
        lag_days: Number of days to lag the metric (default: 1)
                  Positive lag: metric happens before HRV measurement
        
    Returns:
        DataFrame with date, hrv_avg_ms, and the lagged metric column
        
    Example:
        >>> # Analyze if hard training yesterday affects HRV today
        >>> corr_df = correlate_hrv_with_metric(
        ...     hrv_df, training_df, "training_load", lag_days=1
        ... )
    """
    if "date" not in hrv_df.columns or "hrv_avg_ms" not in hrv_df.columns:
        raise ValueError("hrv_df must contain 'date' and 'hrv_avg_ms' columns")
    
    if "date" not in metric_df.columns or metric_column not in metric_df.columns:
        raise ValueError(f"metric_df must contain 'date' and '{metric_column}' columns")
    
    # Shift metric dates by lag (positive lag = metric happens before HRV)
    metric = metric_df[["date", metric_column]].copy()
    metric["date"] = metric["date"] + pd.Timedelta(days=lag_days)
    
    # Merge on date
    merged = hrv_df[["date", "hrv_avg_ms"]].merge(
        metric, on="date", how="inner", suffixes=("", "_lagged")
    )
    
    return merged.sort_values("date").reset_index(drop=True)


def calculate_recovery_score(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate a composite recovery score from HRV and ANS charge.
    
    Args:
        df: DataFrame with hrv_avg_ms and ans_charge columns
        
    Returns:
        DataFrame copy with new column: recovery_score (0-100 scale)
        Combines normalized HRV and ANS charge.
    """
    required_cols = ["hrv_avg_ms", "ans_charge"]
    if not all(col in df.columns for col in required_cols):
        raise ValueError(f"DataFrame must contain columns: {required_cols}")
    
    df = df.copy()
    
    # Normalize HRV to 0-50 scale (higher is better)
    hrv_min, hrv_max = df["hrv_avg_ms"].min(), df["hrv_avg_ms"].max()
    if hrv_max > hrv_min:
        df["hrv_normalized"] = 50 * (df["hrv_avg_ms"] - hrv_min) / (hrv_max - hrv_min)
    else:
        df["hrv_normalized"] = 25.0  # Fallback if all values are the same
    
    # ANS charge is already 0-10 scale, multiply by 5 to get 0-50
    df["ans_normalized"] = df["ans_charge"] * 5
    
    # Composite recovery score (0-100)
    df["recovery_score"] = df["hrv_normalized"] + df["ans_normalized"]
    
    # Cleanup temp columns
    df = df.drop(columns=["hrv_normalized", "ans_normalized"])
    
    return df
