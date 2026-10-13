"""EDA analysis for sql-analytics-case-study.

Recomputes the README headline claims (truth check) and gathers the numbers
used in reports/eda/eda-sql-analytics-2026-10-13.md.

Run with the shared EDA venv:
    /Users/nikitaboarkin/Desktop/00 ide/00 portfolio/.eda-tools/.venv/bin/python \
        reports/eda/scripts/eda_analysis.py

Read-only: does not touch project source/data/tests.
"""

from __future__ import annotations

import json
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]  # project root
DATA = ROOT / "data"
DB = DATA / "analytics.duckdb"
RETAIL = DATA / "realdata" / "online_retail.parquet"

OUT: dict[str, object] = {}


def section(name: str) -> None:
    print(f"\n===== {name} =====")


# ---------------------------------------------------------------- synthetic
users = pd.read_csv(DATA / "users.csv", parse_dates=["signup_date"])
orders = pd.read_csv(DATA / "orders.csv", parse_dates=["order_ts"])
events = pd.read_csv(DATA / "events.csv", parse_dates=["event_time"])
subs = pd.read_csv(DATA / "subscriptions.csv", parse_dates=["started_at"])
refunds = pd.read_csv(DATA / "refunds.csv", parse_dates=["refunded_at"])
cancels = pd.read_csv(
    DATA / "subscription_cancellations.csv", parse_dates=["cancelled_at"]
)

section("ROW COUNTS")
counts = {
    "users": len(users),
    "orders": len(orders),
    "events": len(events),
    "subscriptions": len(subs),
    "refunds": len(refunds),
    "cancellations": len(cancels),
}
print(counts)
OUT["row_counts"] = counts

# ---- 01 funnel (session-level, mirrors case 01) --------------------------
section("01 FUNNEL (session-level)")
order = ["app_open", "view_item", "add_to_cart", "checkout", "purchase"]
funnel = (
    events[events["event_name"].isin(order)]
    .groupby("event_name")["session_id"]
    .nunique()
)
funnel = funnel.reindex(order)
f_overall = (funnel / funnel.iloc[0] * 100).round(2)
f_step = (funnel / funnel.shift(1) * 100).round(2)
f_drop = (100 - f_step).round(2)
funnel_df = pd.DataFrame(
    {
        "sessions": funnel,
        "overall_pct": f_overall,
        "step_pct": f_step,
        "step_drop_pct": f_drop,
    }
)
print(funnel_df)
OUT["funnel"] = funnel_df.reset_index().to_dict("records")

# ---- 02 N-day retention (mirrors case 02) --------------------------------
section("02 N-DAY RETENTION")
active = events[["user_id", "event_time"]].copy()
active["d"] = active["event_time"].dt.normalize()
flags = active.merge(users[["user_id", "signup_date"]], on="user_id", how="right")
for n in (1, 7, 30):
    day = flags["signup_date"] + pd.Timedelta(days=n)
    flags[f"d{n}"] = (flags["d"] == day).astype(int)
per_user = flags.groupby("user_id")[["d1", "d7", "d30"]].max()
retention = (per_user.mean() * 100).round(2)
print("overall:", retention.to_dict())
cohort = users.copy()
cohort["cohort"] = cohort["signup_date"].dt.to_period("M").astype(str)
cohort = cohort.join(per_user, on="user_id")
by_cohort = (cohort.groupby("cohort")[["d1", "d7", "d30"]].mean() * 100).round(2)
print(by_cohort)
OUT["retention_overall"] = {k: float(v) for k, v in retention.items()}
OUT["retention_by_cohort"] = by_cohort.reset_index().to_dict("records")

# ---- 19 repeat purchase --------------------------------------------------
section("19 REPEAT PURCHASE")
buyer = orders.groupby("user_id").agg(orders=("order_id", "count"))
repeat = int((buyer["orders"] >= 2).sum())
buyers = int(len(buyer))
repeat_rate = round(100 * repeat / buyers, 2)
print({"buyers": buyers, "repeat_buyers": repeat, "repeat_rate_pct": repeat_rate})
OUT["repeat"] = {
    "buyers": buyers,
    "repeat_buyers": repeat,
    "repeat_rate_pct": repeat_rate,
}

# ---- 09 A/B conversion ---------------------------------------------------
section("09 A/B CONVERSION")
conv = (
    users.merge(
        orders[["user_id"]].drop_duplicates(), on="user_id", how="left", indicator=True
    )
    .assign(purchased=lambda d: (d["_merge"] == "both").astype(int))
    .groupby("ab_variant")
    .agg(users=("user_id", "size"), purchasers=("purchased", "sum"))
)
conv["conv_pct"] = (conv["purchasers"] / conv["users"] * 100).round(2)
print(conv)
p0 = conv.loc["control", "purchasers"] / conv.loc["control", "users"]
p1 = conv.loc["treatment", "purchasers"] / conv.loc["treatment", "users"]
n0, n1 = conv.loc["control", "users"], conv.loc["treatment", "users"]
p_pool = (conv.loc["control", "purchasers"] + conv.loc["treatment", "purchasers"]) / (
    n0 + n1
)
z = (p1 - p0) / np.sqrt(p_pool * (1 - p_pool) * (1 / n1 + 1 / n0))
print({"p0_pct": round(p0 * 100, 2), "p1_pct": round(p1 * 100, 2), "z": round(z, 2)})
OUT["ab"] = {
    "control_pct": round(p0 * 100, 2),
    "treatment_pct": round(p1 * 100, 2),
    "z": round(float(z), 2),
    "n0": int(n0),
    "n1": int(n1),
}

# ---- orders: amount by segment ------------------------------------------
section("ORDERS AMOUNT BY CATEGORY")
cat = orders.groupby("product_category")["amount"].agg(["count", "mean", "sum"])
cat["share"] = (cat["sum"] / cat["sum"].sum() * 100).round(1)
cat["vs_overall"] = ((cat["mean"] / orders["amount"].mean() - 1) * 100).round(1)
cat = cat.sort_values("mean", ascending=False)
print(cat)
OUT["orders_by_category"] = cat.reset_index().to_dict("records")
print(
    "gap max/min mean =",
    round(cat["mean"].max() / cat["mean"].min(), 3),
)

# ---- subscriptions MRR / churn ------------------------------------------
section("SUBSCRIPTIONS")
print(subs.groupby("plan")["amount"].agg(["count", "sum", "mean"]))
print("total sub revenue:", round(subs["amount"].sum(), 2))
print("refunds total:", round(refunds["amount"].sum(), 2))
print("cancellations:", len(cancels), "of", len(subs))

# ---------------------------------------------------------------- real data
section("26 REAL DATA (online_retail)")
con = duckdb.connect()
retail = con.execute(
    f"""
    SELECT COUNT(*) AS lines,
           MIN(invoice_ts) AS min_ts,
           MAX(invoice_ts) AS max_ts,
           SUM(is_cancellation::INT) AS cancellations,
           SUM(CASE WHEN customer_id IS NULL THEN 1 ELSE 0 END) AS guest_lines
    FROM read_parquet('{RETAIL}')
    """
).df()
print(retail.to_dict("records")[0])
OUT["retail_overview"] = retail.to_dict("records")[0]

rc = con.execute(
    f"""
    WITH invoices AS (
        SELECT customer_id, invoice, SUM(quantity * price) AS inv_rev
        FROM read_parquet('{RETAIL}')
        WHERE customer_id IS NOT NULL AND NOT is_cancellation
          AND quantity > 0 AND price > 0
        GROUP BY customer_id, invoice
    ),
    per_cust AS (
        SELECT customer_id, COUNT(*) AS orders, SUM(inv_rev) AS revenue
        FROM invoices GROUP BY customer_id
    )
    SELECT COUNT(*) AS customers,
           SUM(CASE WHEN orders >= 2 THEN 1 ELSE 0 END) AS repeat_customers,
           ROUND(100.0 * SUM(CASE WHEN orders >= 2 THEN 1 ELSE 0 END) / COUNT(*), 2) AS repeat_pct,
           ROUND(SUM(revenue), 0) AS revenue
    FROM per_cust
    """
).df()
print(rc.to_dict("records")[0])
OUT["retail_repeat"] = rc.to_dict("records")[0]

buckets = con.execute(
    f"""
    WITH invoices AS (
        SELECT customer_id, invoice, SUM(quantity * price) AS inv_rev
        FROM read_parquet('{RETAIL}')
        WHERE customer_id IS NOT NULL AND NOT is_cancellation
          AND quantity > 0 AND price > 0
        GROUP BY customer_id, invoice
    ),
    per_cust AS (
        SELECT customer_id, COUNT(*) AS orders, SUM(inv_rev) AS revenue
        FROM invoices GROUP BY customer_id
    ),
    bucketed AS (
        SELECT CASE WHEN orders = 1 THEN '1' WHEN orders = 2 THEN '2'
                    WHEN orders <= 5 THEN '3-5' WHEN orders <= 10 THEN '6-10'
                    ELSE '11+' END AS bucket, revenue
        FROM per_cust
    )
    SELECT bucket, COUNT(*) AS customers,
           ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS cust_share,
           ROUND(SUM(revenue), 0) AS revenue,
           ROUND(100.0 * SUM(revenue) / SUM(SUM(revenue)) OVER (), 2) AS rev_share
    FROM bucketed GROUP BY bucket ORDER BY MIN(CASE bucket WHEN '1' THEN 1 WHEN '2' THEN 2
        WHEN '3-5' THEN 3 WHEN '6-10' THEN 4 ELSE 5 END)
    """
).df()
print(buckets)
OUT["retail_buckets"] = buckets.to_dict("records")

# concentration: top decile / top 15% of customers by revenue
concentration = con.execute(
    f"""
    WITH invoices AS (
        SELECT customer_id, invoice, SUM(quantity * price) AS inv_rev
        FROM read_parquet('{RETAIL}')
        WHERE customer_id IS NOT NULL AND NOT is_cancellation
          AND quantity > 0 AND price > 0
        GROUP BY customer_id, invoice
    ),
    per_cust AS (
        SELECT customer_id, SUM(inv_rev) AS revenue FROM invoices GROUP BY customer_id
    ),
    ranked AS (
        SELECT revenue, NTILE(10) OVER (ORDER BY revenue DESC) AS decile,
               PERCENT_RANK() OVER (ORDER BY revenue DESC) AS pr
        FROM per_cust
    )
    SELECT
      ROUND(100.0 * SUM(CASE WHEN decile = 1 THEN revenue ELSE 0 END) / SUM(revenue), 2) AS top_decile_pct,
      ROUND(100.0 * SUM(CASE WHEN pr <= 0.15 THEN revenue ELSE 0 END) / SUM(revenue), 2) AS top_15_pct,
      ROUND(100.0 * SUM(CASE WHEN decile <= 2 THEN revenue ELSE 0 END) / SUM(revenue), 2) AS top_20_pct
    FROM ranked
    """
).df()
print(concentration.to_dict("records")[0])
OUT["retail_concentration"] = concentration.to_dict("records")[0]

# retail: cancellation magnitude (revenue impact of negatives)
cancel_rev = con.execute(
    f"""
    SELECT ROUND(SUM(CASE WHEN is_cancellation THEN quantity * price ELSE 0 END), 0) AS cancel_rev,
           ROUND(SUM(CASE WHEN NOT is_cancellation THEN quantity * price ELSE 0 END), 0) AS gross_rev
    FROM read_parquet('{RETAIL}')
    """
).df()
print(cancel_rev.to_dict("records")[0])
OUT["retail_cancel_rev"] = cancel_rev.to_dict("records")[0]

# ---- truth-check summary -------------------------------------------------
section("TRUTH-CHECK SUMMARY")
checks = {
    "funnel_cart_to_checkout_drop_pct": round(float(f_drop.loc["checkout"]), 2),
    "funnel_view_to_cart_drop_pct": round(float(f_drop.loc["add_to_cart"]), 2),
    "d1_overall": float(retention["d1"]),
    "d30_overall": float(retention["d30"]),
    "repeat_rate_pct": repeat_rate,
    "ab_control_pct": round(p0 * 100, 2),
    "ab_treatment_pct": round(p1 * 100, 2),
    "retail_repeat_pct": float(rc.loc[0, "repeat_pct"]),
    "retail_top_15_pct": float(concentration.loc[0, "top_15_pct"]),
}
print(json.dumps(checks, indent=2))
OUT["truth_check"] = checks

out_path = Path(__file__).resolve().parent / "eda_analysis_output.json"
out_path.write_text(json.dumps(OUT, indent=2, default=str))
print(f"\nWrote {out_path}")
