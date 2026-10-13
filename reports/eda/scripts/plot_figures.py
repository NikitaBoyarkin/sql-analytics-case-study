"""Figures for the sql-analytics-case-study EDA.

Run with the shared EDA venv:
    /Users/nikitaboarkin/Desktop/00 ide/00 portfolio/.eda-tools/.venv/bin/python \
        reports/eda/scripts/plot_figures.py

Outputs PNGs into reports/eda/figures/. Light theme, OO style, English labels.
"""

from __future__ import annotations

import warnings
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import duckdb
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "data"
FIG = ROOT / "reports" / "eda" / "figures"
FIG.mkdir(parents=True, exist_ok=True)

plt.rcParams.update(
    {
        "font.family": ["DejaVu Sans", "sans-serif"],
        "axes.unicode_minus": False,
        "figure.dpi": 150,
        "savefig.dpi": 300,
    }
)

# ---- data ----------------------------------------------------------------
users = pd.read_csv(DATA / "users.csv", parse_dates=["signup_date"])
orders = pd.read_csv(DATA / "orders.csv", parse_dates=["order_ts"])
events = pd.read_csv(DATA / "events.csv", parse_dates=["event_time"])


def save(fig, name: str) -> None:
    path = FIG / name
    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print("wrote", path)


# ---- fig 1: funnel steps --------------------------------------------------
def fig_funnel() -> None:
    order = ["app_open", "view_item", "add_to_cart", "checkout", "purchase"]
    counts = (
        events[events["event_name"].isin(order)]
        .groupby("event_name")["session_id"]
        .nunique()
        .reindex(order)
    )
    step_pct = (counts / counts.shift(1) * 100).round(1)
    drop = (100 - step_pct).round(1)

    fig, ax = plt.subplots(figsize=(10, 6), layout="constrained")
    bars = ax.bar(
        range(len(counts)),
        counts.values,
        color="#4C78A8",
        edgecolor="black",
        width=0.62,
    )
    ax.set_xticks(range(len(counts)))
    ax.set_xticklabels([c.replace("_", "\n") for c in counts.index])
    ax.set(
        xlabel="Funnel step (session-level)",
        ylabel="Distinct sessions",
        title="Session funnel — the 54% drop is view_item→add_to_cart, not cart→checkout",
    )
    for i, (b, n) in enumerate(zip(bars, counts.values, strict=True)):
        ax.annotate(
            f"{n:,}",
            (b.get_x() + b.get_width() / 2, n),
            ha="center",
            va="bottom",
            fontsize=10,
            fontweight="bold",
        )
        if i > 0:
            ax.annotate(
                f"−{drop.iloc[i]:.0f}%",
                (b.get_x() + b.get_width() / 2, n + counts.max() * 0.06),
                ha="center",
                va="bottom",
                fontsize=10,
                color="#C44E52",
                fontweight="bold",
            )
    ax.set_ylim(0, counts.max() * 1.18)
    ax.grid(axis="y", alpha=0.3)
    ax.annotate(
        "sharpest drop: cart→checkout = 77.8%\n(README headline says 54% here;\n54% is the view→cart drop)",
        xy=(0.42, 0.72),
        xycoords="axes fraction",
        fontsize=9,
        bbox=dict(boxstyle="round", fc="#FFF3CD", ec="#B8860B", alpha=0.9),
    )
    save(fig, "fig1_funnel_steps.png")


# ---- fig 2: order amount distribution (linear + log) ----------------------
def fig_amount_distribution() -> None:
    amt = orders["amount"]
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), layout="constrained")
    axes[0].hist(amt, bins=40, color="#4C78A8", edgecolor="black", alpha=0.85)
    axes[0].axvline(
        amt.median(), color="#C44E52", lw=2, label=f"median {amt.median():.2f}"
    )
    axes[0].axvline(
        amt.mean(), color="#F58518", lw=2, ls="--", label=f"mean {amt.mean():.2f}"
    )
    axes[0].set(
        xlabel="Order amount ($)",
        ylabel="Orders",
        title=f"Order amount — right-skewed (skew {amt.skew():.2f})",
    )
    axes[0].legend(frameon=False)

    axes[1].hist(np.log10(amt), bins=40, color="#54A24B", edgecolor="black", alpha=0.85)
    axes[1].set(
        xlabel="log10(order amount)",
        ylabel="Orders",
        title="Same amounts on a log10 scale — near-normal core",
    )
    for ax in axes:
        ax.grid(alpha=0.3)
    save(fig, "fig2_order_amount_distribution.png")


# ---- fig 3: purchase conversion by channel (metric by segment) ------------
def fig_conversion_by_channel() -> None:
    buyers = orders[["user_id"]].drop_duplicates().assign(b=1)
    u = users.merge(buyers, on="user_id", how="left")
    u["b"] = u["b"].fillna(0).astype(int)
    g = u.groupby("channel")["b"].agg(["size", "sum"])
    g["conv_pct"] = g["sum"] / g["size"] * 100
    g = g.sort_values("conv_pct", ascending=False)

    fig, ax = plt.subplots(figsize=(9, 6), layout="constrained")
    bars = ax.bar(
        g.index, g["conv_pct"], color="#4C78A8", edgecolor="black", width=0.62
    )
    overall = u["b"].mean() * 100
    ax.axhline(
        overall, color="#C44E52", ls="--", lw=1.5, label=f"overall {overall:.2f}%"
    )
    ax.bar_label(bars, fmt="%.2f%%", padding=3, fontsize=10)
    ax.set(
        xlabel="Acquisition channel",
        ylabel="User purchase conversion (%)",
        title="Purchase conversion by channel — email 6.3% vs paid_search 3.0% (×2.1)",
    )
    ax.set_ylim(0, g["conv_pct"].max() * 1.2)
    ax.legend(frameon=False)
    ax.grid(axis="y", alpha=0.3)
    save(fig, "fig3_conversion_by_channel.png")


# ---- fig 4: weekly order revenue with anomaly -----------------------------
def fig_weekly_revenue() -> None:
    wk = (
        orders.set_index("order_ts")
        .resample("W")["amount"]
        .agg(["sum", "count"])
        .rename(columns={"sum": "revenue", "count": "orders"})
    )
    fig, ax = plt.subplots(figsize=(11, 6), layout="constrained")
    ax.plot(
        wk.index,
        wk["revenue"],
        marker="o",
        color="#4C78A8",
        lw=2,
        label="weekly revenue",
    )
    ax.set(
        xlabel="Week",
        ylabel="Order revenue ($)",
        title="Weekly order revenue — ramp-up then plateau; one +59% spike (2024-06-16)",
    )
    peak = wk["revenue"].idxmax()
    ax.annotate(
        f"+59% week\n${wk.loc[peak, 'revenue']:.0f}",
        xy=(peak, wk.loc[peak, "revenue"]),
        xytext=(-90, -55),
        textcoords="offset points",
        arrowprops=dict(arrowstyle="->", color="#C44E52"),
        fontsize=9,
        color="#C44E52",
    )
    ax.grid(alpha=0.3)
    ax.legend(frameon=False)
    save(fig, "fig4_weekly_order_revenue.png")


# ---- fig 5: retention decay by cohort -------------------------------------
def fig_retention() -> None:
    active = events[["user_id", "event_time"]].copy()
    active["d"] = active["event_time"].dt.normalize()
    flags = active.merge(users[["user_id", "signup_date"]], on="user_id", how="right")
    for n in (1, 7, 30):
        flags[f"d{n}"] = (
            flags["d"] == flags["signup_date"] + pd.Timedelta(days=n)
        ).astype(int)
    per_user = flags.groupby("user_id")[["d1", "d7", "d30"]].max()
    coh = users.copy()
    coh["cohort"] = coh["signup_date"].dt.to_period("M").astype(str)
    coh = coh.join(per_user, on="user_id")
    by = (coh.groupby("cohort")[["d1", "d7", "d30"]].mean() * 100).round(2)

    fig, ax = plt.subplots(figsize=(10, 6), layout="constrained")
    for col, label, color in [
        ("d1", "D1 retention", "#4C78A8"),
        ("d7", "D7 retention", "#F58518"),
        ("d30", "D30 retention", "#C44E52"),
    ]:
        ax.plot(by.index, by[col], marker="o", lw=2, label=label, color=color)
    ax.set(
        xlabel="Signup-month cohort",
        ylabel="Retention (%)",
        title="Retention decays 19.5% (D1) → 14.7% (D7) → 4.2% (D30); June D30 censored",
    )
    ax.annotate(
        "June D30 = 0%\n(no 30-day window yet)",
        xy=(by.index[-1], by["d30"].iloc[-1]),
        xytext=(-120, 40),
        textcoords="offset points",
        arrowprops=dict(arrowstyle="->", color="grey"),
        fontsize=9,
        color="grey",
    )
    ax.legend(frameon=False)
    ax.grid(alpha=0.3)
    save(fig, "fig5_retention_decay.png")


# ---- fig 6: real-data repeat & concentration ------------------------------
def fig_retail_concentration() -> None:
    con = duckdb.connect()
    buckets = con.execute(
        f"""
        WITH invoices AS (
            SELECT customer_id, invoice, SUM(quantity * price) AS inv_rev
            FROM read_parquet('{DATA / "realdata" / "online_retail.parquet"}')
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
        SELECT bucket,
               ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS cust_share,
               ROUND(100.0 * SUM(revenue) / SUM(SUM(revenue)) OVER (), 2) AS rev_share
        FROM bucketed GROUP BY bucket
        ORDER BY MIN(CASE bucket WHEN '1' THEN 1 WHEN '2' THEN 2 WHEN '3-5' THEN 3
                    WHEN '6-10' THEN 4 ELSE 5 END)
        """
    ).df()

    x = np.arange(len(buckets))
    w = 0.38
    fig, ax = plt.subplots(figsize=(10, 6), layout="constrained")
    ax.bar(
        x - w / 2,
        buckets["cust_share"],
        w,
        label="% of customers",
        color="#4C78A8",
        edgecolor="black",
    )
    ax.bar(
        x + w / 2,
        buckets["rev_share"],
        w,
        label="% of revenue",
        color="#F58518",
        edgecolor="black",
    )
    ax.set_xticks(x)
    ax.set_xticklabels(buckets["bucket"])
    ax.set(
        xlabel="Order count bucket (UCI Online Retail II, real data)",
        ylabel="Share (%)",
        title="Real data flips the synthetic story: 14.9% of customers (11+) carry 65% of revenue",
    )
    ax.legend(frameon=False)
    ax.grid(axis="y", alpha=0.3)
    for i, (c, r) in enumerate(
        zip(buckets["cust_share"], buckets["rev_share"], strict=True)
    ):
        ax.text(i - w / 2, c + 0.7, f"{c:.1f}", ha="center", fontsize=8)
        ax.text(
            i + w / 2, r + 0.7, f"{r:.1f}", ha="center", fontsize=8, color="#B5651D"
        )
    ax.set_ylim(0, max(buckets["rev_share"].max(), buckets["cust_share"].max()) * 1.18)
    save(fig, "fig6_retail_repeat_concentration.png")


if __name__ == "__main__":
    fig_funnel()
    fig_amount_distribution()
    fig_conversion_by_channel()
    fig_weekly_revenue()
    fig_retention()
    fig_retail_concentration()
    print("done")
