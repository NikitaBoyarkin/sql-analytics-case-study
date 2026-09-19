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


def test_16_sessionization():
    df = _run("16_sessionization.sql")
    s = {m: v for m, v in zip(df["metric"], df["value"])}
    assert int(s["derived_sessions"]) <= int(s["true_sessions"])
    assert float(s["fidelity_pct"]) > 95
    assert int(s["merged_pairs"]) > 0
    # depth buckets partition the derived sessions exactly
    assert int(s["sessions_1_event"]) + int(s["sessions_2_3_events"]) + int(
        s["sessions_4_5_events"]
    ) + int(s["sessions_6plus_events"]) == int(s["derived_sessions"])
    # most sessions are shallow bursts (2-3 events)
    assert int(s["sessions_2_3_events"]) > int(s["sessions_1_event"])
    assert int(s["sessions_6plus_events"]) < 1000


def test_17_lifecycle():
    df = _run("17_lifecycle.sql")
    assert len(df) == 26  # Jan 1 .. Jun 30 -> 26 Monday-started weeks
    # the 3 active states must sum to 100% of the active base
    assert (df["new_pct"] + df["returning_pct"] + df["resurrecting_pct"]).sub(
        100
    ).abs().max() < 1.0
    assert (df["active_users"] > 0).all()
    assert (df["dormant_users"] >= 0).all()
    assert df["new_pct"].iloc[0] == 100.0  # week 1 is all-new
    # late weeks: resurrecting is a material share of the base
    assert (df["resurrecting_pct"].tail(10) > 25).all()


def test_18_cohort_revenue_retention():
    df = _run("18_cohort_revenue_retention.sql")
    assert (
        len(df) == 19
    )  # triangle: Jan 5 + Feb 4 + Mar 4 + Apr 3 + May 2 + Jun 1 = 19 rows
    assert (df["pct_of_period0"].between(0, 100)).all()
    assert df.loc[df.period == 0, "pct_of_period0"].eq(100.0).all()
    for cohort, g in df.groupby("cohort"):
        assert g["pct_of_period0"].is_monotonic_decreasing
    assert (df["ltv_per_user"] >= 0).all()
    assert (df["cum_revenue"] >= df["revenue"] - 0.01).all()


def test_19_repeat_purchase():
    df = _run("19_repeat_purchase.sql")
    s = {m: v for m, v in zip(df["metric"], df["value"])}
    assert int(s["buyers"]) == 896
    assert int(s["repeat_buyers"]) >= 30
    assert float(s["repeat_rate_pct"]) < 10  # one-and-done purchase engine
    assert int(s["buyers_1_order"]) + int(s["buyers_2_orders"]) + int(
        s["buyers_3_orders"]
    ) + int(s["buyers_4plus_orders"]) == int(s["buyers"])
    assert int(float(s["median_days_between"])) <= int(float(s["p90_days_between"]))


def test_20_rfm():
    df = _run("20_rfm.sql")
    assert len(df) == 7
    assert set(df["segment"]) == {
        "Champions",
        "Loyal",
        "Regular",
        "At Risk",
        "Hibernating",
        "Big Spenders",
        "Promising",
    }
    assert int(df["buyers"].sum()) == 896
    assert df["pct_of_revenue"].sum() > 99
    # frequency barely discriminates (repeat rate ~3.5%) -> whale tier is tiny
    assert int(df.loc[df.segment == "Big Spenders", "buyers"].iloc[0]) < 30


def test_21_subscription_churn():
    df = _run("21_subscription_churn.sql")
    assert len(df) == 5  # Feb .. Jun
    assert (df["subs_at_start"] > 0).all()
    assert (df["churned"] >= 0).all()
    assert (df["churned"] <= df["subs_at_start"]).all()
    for col in ("logo_churn_pct", "mrr_churn_pct"):
        assert df[col].between(0, 100).all()
    # MRR churn tracks logo churn (flat-price plans): both rise together
    assert df["logo_churn_pct"].iloc[-1] > df["logo_churn_pct"].iloc[0]
    assert df["mrr_churn_pct"].iloc[-1] > df["mrr_churn_pct"].iloc[0]
    assert df["subs_at_start"].is_monotonic_increasing


def test_22_refunds_net_revenue():
    df = _run("22_refunds_net_revenue.sql")
    assert len(df) == 6
    assert (df["net"] <= df["gross"] + 0.01).all()
    assert (df["refunded"] >= 0).all()
    assert df["refund_rate_pct"].between(0, 100).all()
    # gross and net roughly track each other (refund rate is small)
    assert (df["net"] > 0.8 * df["gross"]).all()


def test_23_pareto_concentration():
    df = _run("23_pareto_concentration.sql")
    assert len(df) == 10
    assert df["revenue"].is_monotonic_decreasing  # highest decile first
    assert df["pct_of_revenue"].between(0, 100).all()
    assert df["pct_of_buyers"].between(9, 11).all()
    # cumulative share is monotone and ends at 100
    assert df["cum_pct"].is_monotonic_increasing
    assert abs(df["cum_pct"].iloc[-1] - 100.0) < 0.1
    # top decile > bottom decile by revenue share
    assert df["pct_of_revenue"].iloc[0] > df["pct_of_revenue"].iloc[-1]


def test_24_anomaly_detection():
    df = _run("24_anomaly_detection.sql")
    assert len(df) == 172  # days with >=7 days of history
    assert (df["daily_revenue"] > 0).all()
    assert (df["z_mad"].notna()).all()
    flagged = df[df["anomalous"] == "YES"]
    assert len(flagged) == 4  # exactly 4 days cross |z| >= 3
    # every flagged day is a genuine outlier (|z| >= 3)
    assert (flagged["z_mad"].abs() >= 3).all()
    assert df["d"].is_monotonic_increasing


def test_25_subscription_conversion():
    df = _run("25_subscription_conversion.sql")
    s = {m: v for m, v in zip(df["metric"], df["value"])}
    assert int(s["purchasers"]) == 896
    assert int(s["subscribers"]) == 268
    assert float(s["conversion_pct"]) > 25
    assert int(float(s["median_days_to_convert"])) <= int(
        float(s["p90_days_to_convert"])
    )
    assert int(s["monthly_subs"]) + int(s["annual_subs"]) == int(s["subscribers"])


def test_26_realdata_repeat_concentration():
    df = _run("26_realdata_repeat_concentration.sql")
    assert list(df["bucket"]) == ["1", "2", "3-5", "6-10", "11+"]
    # shares must each sum to ~100%
    assert abs(df["customer_share_pct"].sum() - 100) < 0.1
    assert abs(df["revenue_share_pct"].sum() - 100) < 0.1
    # revenue share rises monotonically with order count
    assert df["revenue_share_pct"].is_monotonic_increasing
    # one-time buyers are a minority of revenue; the top bucket dominates
    assert float(df.loc[df.bucket == "1", "revenue_share_pct"].iloc[0]) < 5
    assert float(df.loc[df.bucket == "11+", "revenue_share_pct"].iloc[0]) > 60
    # repeat customers (any bucket past "1") are the majority
    repeat_share = df.loc[df.bucket != "1", "customer_share_pct"].sum()
    assert repeat_share > 70
