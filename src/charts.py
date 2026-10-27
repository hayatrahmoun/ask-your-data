"""Pick a sensible chart automatically from the shape of a query result."""
import re

import pandas as pd

_TIME_NAMES = {"year", "year_month", "month", "date", "quarter"}


def pick_chart(df: pd.DataFrame):
    """Return (kind, plot_df) with kind in {'line', 'bar'}, or None if a table is better."""
    if df.shape[1] < 2 or not (2 <= len(df) <= 60):
        return None

    first = df.columns[0]
    numeric = [c for c in df.columns[1:] if pd.api.types.is_numeric_dtype(df[c])]
    if not numeric:
        return None
    if pd.api.types.is_numeric_dtype(df[first]) and str(first).lower() not in _TIME_NAMES:
        return None  # first column must be a label, not a measure

    labels = df[first].astype(str)
    is_time = str(first).lower() in _TIME_NAMES or labels.str.match(r"^\d{4}(-\d{2})?$").all()
    plot_df = df[numeric[:3]].copy()
    plot_df.index = labels
    return ("line" if is_time else "bar"), plot_df
