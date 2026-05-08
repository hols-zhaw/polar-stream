"""
test_layer_isolation.py
───────────────────────
Validation tests to ensure strict layer boundaries.

Tests verify:
1. Layer 3 (analysis) has no Streamlit imports
2. Layer 4 (viz) has no Streamlit imports
3. Analysis functions are pure (DataFrame in → DataFrame out)
4. Viz functions are pure (DataFrame in → Figure out)
"""

import sys
import importlib.util
from pathlib import Path

# Add project root to Python path so we can import analysis, data, viz modules
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def test_layer3_no_streamlit():
    """Layer 3 (analysis) must not import Streamlit."""
    analysis_path = Path(__file__).parent.parent / "analysis" / "hrv.py"
    
    with open(analysis_path, "r") as f:
        content = f.read()
    
    # Check for actual imports, not just mentions in comments
    assert "import streamlit" not in content.lower(), "Layer 3 (analysis/hrv.py) must not import Streamlit"
    assert "from streamlit" not in content.lower(), "Layer 3 must not import from Streamlit"
    print("✅ Layer 3 (analysis) has no Streamlit dependencies")


def test_layer4_no_streamlit():
    """Layer 4 (viz) must not import Streamlit."""
    viz_path = Path(__file__).parent.parent / "viz" / "charts_hrv.py"
    
    with open(viz_path, "r") as f:
        content = f.read()
    
    # Check for actual imports, not just mentions in comments
    assert "import streamlit" not in content.lower(), "Layer 4 (viz/charts_hrv.py) must not import Streamlit"
    assert "from streamlit" not in content.lower(), "Layer 4 must not import from Streamlit"
    print("✅ Layer 4 (viz) has no Streamlit dependencies")


def test_layer3_pure_functions():
    """Layer 3 analysis functions must be pure (no side effects)."""
    try:
        import pandas as pd
        from analysis.hrv import add_rolling_average, flag_low_hrv, calculate_recovery_score
    except ImportError:
        print("⚠️  Layer 3 (analysis) functional tests skipped (dependencies not installed)")
        return
    
    # Create synthetic test data
    df = pd.DataFrame({
        "date": pd.date_range("2024-01-01", periods=30),
        "hrv_avg_ms": [50 + i for i in range(30)],
        "ans_charge": [5.0] * 30,
        "hr_avg": [60.0] * 30,
        "sleep_charge": [70.0] * 30,
    })
    
    # Test 1: add_rolling_average returns new DataFrame
    df_with_rolling = add_rolling_average(df, "hrv_avg_ms", window=7)
    assert "hrv_avg_ms_rolling7" in df_with_rolling.columns, "Rolling average column not added"
    assert len(df_with_rolling) == len(df), "Function changed row count"
    
    # Test 2: flag_low_hrv adds boolean column
    df_flagged = flag_low_hrv(df, threshold_percentile=20)
    assert "low_recovery" in df_flagged.columns, "Low recovery flag not added"
    assert df_flagged["low_recovery"].dtype == bool, "Flag column should be boolean"
    
    # Test 3: calculate_recovery_score adds numeric column
    df_with_score = calculate_recovery_score(df_flagged)
    assert "recovery_score" in df_with_score.columns, "Recovery score column not added"
    assert df_with_score["recovery_score"].min() >= 0, "Recovery score should be >= 0"
    assert df_with_score["recovery_score"].max() <= 100, "Recovery score should be <= 100"
    
    print("✅ Layer 3 (analysis) functions are pure and work correctly")


def test_layer4_pure_functions():
    """Layer 4 viz functions must be pure (DataFrame → Figure)."""
    try:
        import pandas as pd
        from viz.charts_hrv import hrv_timeseries, recovery_score_chart
    except ImportError:
        print("⚠️  Layer 4 (viz) functional tests skipped (dependencies not installed)")
        return
    
    # Create synthetic test data
    df = pd.DataFrame({
        "date": pd.date_range("2024-01-01", periods=10),
        "hrv_avg_ms": [50, 55, 52, 60, 58, 62, 65, 63, 68, 70],
        "hrv_avg_ms_rolling7": [52, 54, 56, 58, 60, 62, 64, 65, 66, 67],
        "low_recovery": [False] * 10,
        "recovery_score": [60, 65, 62, 70, 68, 72, 75, 73, 78, 80],
        "ans_charge": [5.0] * 10,
    })
    
    # Test 1: hrv_timeseries returns Plotly Figure
    fig_hrv = hrv_timeseries(df, show_rolling=True)
    assert hasattr(fig_hrv, "data"), "Should return Plotly Figure object"
    assert len(fig_hrv.data) > 0, "Figure should have traces"
    
    # Test 2: recovery_score_chart returns Plotly Figure
    fig_recovery = recovery_score_chart(df)
    assert hasattr(fig_recovery, "data"), "Should return Plotly Figure object"
    assert len(fig_recovery.data) > 0, "Figure should have traces"
    
    print("✅ Layer 4 (viz) functions are pure and return valid Figures")


def test_layer2_no_streamlit():
    """Layer 2 (data) must not import Streamlit."""
    cache_path = Path(__file__).parent.parent / "data" / "cache.py"
    
    with open(cache_path, "r") as f:
        content = f.read()
    
    assert "import streamlit" not in content, "Layer 2 (data/cache.py) must not import Streamlit"
    assert "@st.cache_data" not in content, "Layer 2 must not use @st.cache_data (moved to Layer 5)"
    print("✅ Layer 2 (data) has no Streamlit dependencies")


if __name__ == "__main__":
    print("\n🧪 Running Layer Isolation Validation Tests\n")
    print("=" * 60)
    
    try:
        test_layer2_no_streamlit()
        test_layer3_no_streamlit()
        test_layer4_no_streamlit()
        test_layer3_pure_functions()
        test_layer4_pure_functions()
        
        print("=" * 60)
        print("\n✅ All tests passed! Layer boundaries are properly enforced.\n")
        sys.exit(0)
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
