"""Regression tests: each case must run and satisfy key invariants.

Run: uv run --with duckdb --with pandas --with numpy --with pytest pytest -q
"""

import pathlib

import duckdb
import pandas as pd

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


def test_11_moving_average_dau():
    df = _run("11_moving_average_dau.sql")
    assert len(df) == 181  # Jan 2 .. Jun 30
    assert (df["dau"] > 0).all()
    assert (df["dau_ma7"] > 0).all()
    # no right-censoring cliff on the last day (generator truncates, not clamps)
    assert df["dau"].max() < 800
    assert df["d"].is_monotonic_increasing


def test_12_qualify_top_users():
    df = _run("12_qualify_top_users.sql")
    assert len(df) == 10  # 5 countries x top-2
    assert set(df["country"]) == {"RU", "UA", "KZ", "BY", "Other"}
    assert (df.groupby("country")["user_id"].count() == 2).all()
    # revenue strictly descending within each country (QUALIFY ordering)
    for country, g in df.groupby("country"):
        assert g["revenue"].is_monotonic_decreasing


def test_13_pivot_revenue():
    df = _run("13_pivot_revenue.sql")
    assert len(df) == 6  # Jan .. Jun
    assert df["month"].is_monotonic_increasing
    cats = {"beauty", "books", "clothing", "electronics", "home", "sports"}
    assert cats.issubset(df.columns)
    for c in cats:
        assert (df[c] > 0).all()  # every category sells every month


def test_14_recursive_subscription_mrr():
    df = _run("14_recursive_subscription_mrr.sql")
    assert len(df) == 6  # Jan .. Jun, no July (subs capped at window end)
    assert df["month"].iloc[0] == pd.Timestamp("2024-01-01")
    assert df["month"].iloc[-1] == pd.Timestamp("2024-06-01")
    assert df["mrr"].is_monotonic_increasing
    assert (df["mrr"] > 0).all()
    assert df["active_subs"].is_monotonic_increasing


def test_15_percentile_order_amounts():
    df = _run("15_percentile_order_amounts.sql")
    assert len(df) == 6
    # monotone quantiles: median <= p90 <= p99
    assert (df["median_amount"] <= df["p90"]).all()
    assert (df["p90"] <= df["p99"]).all()
    # orders across categories sum to the full orders table
    con = duckdb.connect(str(DB), read_only=True)
    total = con.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    con.close()
    assert int(df["orders"].sum()) == total
