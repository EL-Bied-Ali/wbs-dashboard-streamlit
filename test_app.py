#!/usr/bin/env python3
"""
Dependency smoke test.

Ensures ChronoPlan's core Python deps import and basic objects can be created,
without starting Streamlit UI rendering.
"""

from __future__ import annotations


def test_imports() -> None:
    import pandas as pd
    import plotly.express as px
    import streamlit  # noqa: F401

    df = pd.DataFrame(
        {
            "week": [f"W{i}" for i in range(1, 6)],
            "value": [3, 5, 2, 6, 4],
        }
    )
    fig = px.bar(df, x="week", y="value", title="Smoke")

    assert df.shape == (5, 2)
    assert fig is not None


if __name__ == "__main__":
    test_imports()
    print("PASS")
