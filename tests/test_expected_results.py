"""Regression tests: each case must run and satisfy key invariants.

Run: uv run --with duckdb --with pandas --with numpy --with pytest pytest -q
"""
import pathlib

import duckdb
import pytest

ROOT = pathlib.Path(__file__).parent.parent
CASES = ROOT / "cases"
DB = ROOT / "data" / "analytics.duckdb"


def _run(name: str):
    con = duckdb.connect(str(DB), read_only=True)
    try:
        return con.execute((CASES / name).read_text()).fetchdf()
    finally:
        con.close()


def test_01_funnel_conversion():
    df = _run("01_funnel_conversion.sql")
    assert len(df) == 5
    assert int(df.loc[df.event_name == "app_open", "sessions"].iloc[0]) == 80000
    assert float(df.loc[df.event_name == "app_open", "overall_pct"].iloc[0]) == 100.0
    # funnel must be monotonically non-increasing by session count
    assert df["sessions"].is_monotonic_decreasing


def test_02_n_day_retention():
    df = _run("02_n_day_retention.sql")
    assert len(df) == 6  # 6 signup months
    for col in ("d1_retention", "d7_retention", "d30_retention"):
        assert df[col].between(0, 100).all()


def test_03_rolling_retention():
    df = _run("03_rolling_retention.sql")
    assert len(df) == 6
    for col in ("win_7d", "win_14d", "win_30d", "win_60d"):
        assert df[col].between(0, 100).all()
    # earlier windows should retain >= later windows (decaying) within a cohort
    assert (df["win_7d"] >= df["win_14d"]).all()
    assert (df["win_14d"] >= df["win_30d"]).all()


def test_04_dau_mau_stickiness():
    df = _run("04_dau_mau_stickiness.sql")
    assert (df["dau"] <= df["mau"]).all()
    assert df["stickiness_pct"].between(0, 100).all()
    assert df["d"].is_monotonic_increasing


def test_05_ltv_by_cohort():
    df = _run("05_ltv_by_cohort.sql")
    assert len(df) == 6
    assert (df["revenue"] >= 0).all()
    assert (df["ltv_per_user"] >= 0).all()
    assert df["users"].sum() == 20000  # every user counted in exactly one cohort


def test_06_top_n_by_category():
    df = _run("06_top_n_by_category.sql")
    assert (df["rnk"] <= 3).all()
    # no country has more than 3 ranked rows
    assert (df.groupby("country")["rnk"].count() <= 3).all()
    # ranks within country are contiguous 1..k
    for country, g in df.groupby("country"):
        assert sorted(g["rnk"].tolist()) == list(range(1, len(g) + 1))


def test_07_running_total():
    df = _run("07_running_total.sql")
    assert df["cumulative"].is_monotonic_increasing
    assert abs(df["cumulative"].iloc[-1] - df["daily_revenue"].sum()) < 0.01


def test_08_consecutive_streaks():
    df = _run("08_consecutive_streaks.sql")
    assert (df["longest_streak_days"] >= 1).all()
    assert df["longest_streak_days"].is_monotonic_decreasing


def test_09_ab_test_join():
    df = _run("09_ab_test_join.sql").sort_values("ab_variant").reset_index(drop=True)
    assert set(df["ab_variant"]) == {"control", "treatment"}
    assert int(df["users"].sum()) == 20000
    assert df["conv_pct"].between(0, 100).all()
    # lift on first row is NULL (no previous variant)
    assert df["lift_pp"].isna().iloc[0]


def test_10_revenue_attribution():
    df = _run("10_revenue_attribution.sql")
    assert len(df) == 5  # 5 channels
    assert (df["lifetime_revenue"] >= df["first_touch_revenue"] - 0.01).all()
    assert df["lifetime_revenue"].is_monotonic_decreasing
