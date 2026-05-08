"""
theme.py
────────
Layer 4 — Visualization Theme
Shared color palette and layout defaults for consistent charting.

Pure Python constants—no framework dependencies.
"""

# Color palette inspired by Polar branding
COLORS = {
    "hrv": "#00D9FF",  # Cyan for HRV
    "hr": "#FF6B6B",   # Red for heart rate
    "sleep": "#4ECDC4",  # Teal for sleep
    "deep_sleep": "#1A535C",
    "rem_sleep": "#FFE66D",
    "light_sleep": "#95E1D3",
    "training": "#FF6F61",
    "ans_charge": "#6A0572",
    "recovery": "#4CAF50",
    "poor": "#FF5252",
    "good": "#69F0AE",
    "background": "#0E1117",
    "grid": "rgba(255, 255, 255, 0.1)",
    "text": "#FAFAFA",
}

# Default Plotly layout settings
LAYOUT_DEFAULTS = {
    "plot_bgcolor": "rgba(0,0,0,0)",
    "paper_bgcolor": "rgba(0,0,0,0)",
    "font": {"color": COLORS["text"], "family": "Inter, sans-serif", "size": 12},
    "xaxis": {
        "showgrid": True,
        "gridcolor": COLORS["grid"],
        "zeroline": False,
    },
    "yaxis": {
        "showgrid": True,
        "gridcolor": COLORS["grid"],
        "zeroline": False,
    },
    "hovermode": "x unified",
    "margin": {"t": 60, "r": 20, "b": 60, "l": 60},
}

# Status color mappings
RECHARGE_STATUS_COLORS = {
    "very_poor": "#D32F2F",
    "poor": "#F57C00",
    "compromised": "#FBC02D",
    "sustained": "#7CB342",
    "very_good": "#388E3C",
}
