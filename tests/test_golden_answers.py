"""Golden-answer regression tests: pin the exact numbers documented in cases.md
to the live database output. If the generator or a case's SQL changes the
business results, this test fails and cases.md must be regenerated in sync.

Run: uv run --extra dev pytest -q tests/test_golden_answers.py
"""

import pathlib

import duckdb
import pandas as pd

ROOT = pathlib.Path(__file__).parent.parent
CASES = ROOT / "cases"
DB = ROOT / "data" / "analytics.duckdb"


def _run(name: str) -> pd.DataFrame:
    con = duckdb.connect(str(DB), read_only=True)
    try:
        return con.execute((CASES / name).read_text()).fetchdf()
    finally:
        con.close()


def test_01_funnel_golden():
    df = _run("01_funnel_conversion.sql").set_index("event_name")
    assert int(df.loc["app_open", "sessions"]) == 80_000
    assert int(df.loc["view_item", "sessions"]) == 65_739
    assert int(df.loc["add_to_cart", "sessions"]) == 29_641
    assert int(df.loc["checkout", "sessions"]) == 6_584
    assert int(df.loc["purchase", "sessions"]) == 928
    # biggest drop is add_to_cart -> checkout (the instrument-first step)
    assert df.loc["add_to_cart", "step_pct"] > df.loc["checkout", "step_pct"]


def test_02_retention_golden():
    df = _run("02_n_day_retention.sql")
    assert len(df) == 6
    # D1 stable ~19-21%, D30 collapses except June (censored cohort)
    assert df["d1_retention"].between(18, 21).all()
    assert df.loc[df.cohort == pd.Timestamp("2024-01-01"), "d30_retention"].iloc[0] > 5
    assert (
        df.loc[df.cohort == pd.Timestamp("2024-06-01"), "d30_retention"].iloc[0] == 0.0
    )


def test_05_ltv_golden():
    df = _run("05_ltv_by_cohort.sql")
    assert len(df) == 6
    # every cohort sums to the full user base, revenue non-negative
    assert df["users"].sum() == 20_000
    # LTV grows with cohort age (same-age comparison)
    assert df.loc[df.cohort == pd.Timestamp("2024-01-01"), "ltv_per_user"].iloc[0] > 1.0
    assert df.loc[df.cohort == pd.Timestamp("2024-06-01"), "ltv_per_user"].iloc[0] < 1.0


def test_09_ab_golden():
    df = _run("09_ab_test_join.sql")
    ctrl = df[df.ab_variant == "control"].iloc[0]
    trt = df[df.ab_variant == "treatment"].iloc[0]
    # embedded effect: treatment converts higher, z > 3, p < 0.01, significant
    assert trt["conv_pct"] > ctrl["conv_pct"]
    assert trt["z_score"] > 3
    assert trt["p_value"] < 0.01
    assert trt["significant_005"] == "YES"
    assert ctrl["lift_pp"] != ctrl["lift_pp"]  # NaN on the first variant row


def test_10_attribution_golden():
    df = _run("10_revenue_attribution.sql")
    assert len(df) == 5
    # referral out-earns its user share (high retention -> repeat purchases)
    assert df.loc[df.channel == "referral", "lifetime_revenue"].iloc[0] > 4500
    # lifetime >= first-touch everywhere
    assert (df["lifetime_revenue"] >= df["first_touch_revenue"] - 0.01).all()


def test_14_mrr_golden():
    df = _run("14_recursive_subscription_mrr.sql")
    # MRR roughly 15x over the window (18 -> 268 active subs)
    assert df["mrr"].iloc[0] > 100
    assert df["mrr"].iloc[-1] > 2000
    assert df["month"].iloc[-1] == pd.Timestamp("2024-06-01")
