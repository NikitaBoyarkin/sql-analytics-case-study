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


def test_16_sessionization_golden():
    df = _run("16_sessionization.sql")
    s = {m: v for m, v in zip(df["metric"], df["value"])}
    assert int(s["derived_sessions"]) == 79_700
    assert int(s["true_sessions"]) == 80_000
    assert float(s["fidelity_pct"]) == 99.6
    assert int(s["merged_pairs"]) == 298
    assert float(s["median_events_per_session"]) == 2.0


def test_17_lifecycle_golden():
    df = _run("17_lifecycle.sql")
    assert len(df) == 26
    assert int(df["new_users"].iloc[0]) == 333
    assert int(df["returning_users"].iloc[0]) == 0
    # late-window composition: resurrecting ~1/3 of active, dormant > 1400
    last = df.iloc[-1]
    assert int(last["resurrecting_users"]) > 700
    assert int(last["dormant_users"]) > 1400


def test_18_revenue_retention_golden():
    df = _run("18_cohort_revenue_retention.sql")
    jan0 = df.loc[(df.cohort == pd.Timestamp("2024-01-01")) & (df.period == 0)]
    assert float(jan0["revenue"].iloc[0]) > 2400
    # month-1 retention of the Jan cohort ~85% of period-0
    jan1 = df.loc[(df.cohort == pd.Timestamp("2024-01-01")) & (df.period == 1)]
    assert float(jan1["pct_of_period0"].iloc[0]) > 80
    # month-2 collapse to under 25%
    jan2 = df.loc[(df.cohort == pd.Timestamp("2024-01-01")) & (df.period == 2)]
    assert float(jan2["pct_of_period0"].iloc[0]) < 25


def test_19_repeat_purchase_golden():
    df = _run("19_repeat_purchase.sql")
    s = {m: v for m, v in zip(df["metric"], df["value"])}
    assert int(s["buyers"]) == 896
    assert int(s["repeat_buyers"]) == 31
    assert float(s["repeat_rate_pct"]) == 3.5
    assert int(float(s["median_days_between"])) == 9


def test_20_rfm_golden():
    df = _run("20_rfm.sql")
    assert int(df["buyers"].sum()) == 896
    assert int(df.loc[df.segment == "Champions", "buyers"].iloc[0]) == 166
    assert int(df.loc[df.segment == "Big Spenders", "buyers"].iloc[0]) == 11
