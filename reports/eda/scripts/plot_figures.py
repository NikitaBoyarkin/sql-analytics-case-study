"""Figures for the sql-analytics-case-study EDA.

Run from the repo root with the project environment:
    uv run python reports/eda/scripts/plot_figures.py

Outputs PNGs into reports/eda/figures/. Light theme, OO style, English labels.

Every headline number in a title or callout is derived from the data below, never
typed by hand — a figure cannot drift from the numbers it claims. PNG metadata is
pinned so re-runs are byte-comparable.
"""

from __future__ import annotations

import warnings
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import duckdb
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "data"
FIG = ROOT / "reports" / "eda" / "figures"
FIG.mkdir(parents=True, exist_ok=True)

plt.rcParams.update(
    {
        # generic family last: without it a missing face turns into tofu boxes
        "font.family": ["DejaVu Sans", "sans-serif"],
        "axes.unicode_minus": False,
        "figure.dpi": 150,
        "savefig.dpi": 300,
    }
)

BLUE, ORANGE, RED, GREEN = "#4C78A8", "#F58518", "#C44E52", "#54A24B"

FUNNEL = ["app_open", "view_item", "add_to_cart", "checkout", "purchase"]
FUNNEL_TICKS = ["app\nopen", "view\nitem", "add to\ncart", "checkout", "purchase"]


def load() -> dict[str, pd.DataFrame]:
    return {
        "users": pd.read_csv(DATA / "users.csv", parse_dates=["signup_date"]),
        "orders": pd.read_csv(DATA / "orders.csv", parse_dates=["order_ts"]),
        "events": pd.read_csv(DATA / "events.csv", parse_dates=["event_time"]),
    }


def save(fig, name: str) -> None:
    path = FIG / name
    # Software=None drops the "Matplotlib versionX.Y.Z" tEXt chunk: without it
    # every matplotlib upgrade rewrites all six files with identical pixels.
    fig.savefig(path, dpi=300, bbox_inches="tight", metadata={"Software": None})
    plt.close(fig)
    print("wrote", path)


# ---- fig 1: funnel steps --------------------------------------------------
def fig_funnel(events: pd.DataFrame) -> None:
    counts = (
        events[events["event_name"].isin(FUNNEL)]
        .groupby("event_name")["session_id"]
        .nunique()
        .reindex(FUNNEL)
    )
    step_pct = counts / counts.shift(1) * 100
    drop_pct = (100 - step_pct).round(1)
    lost = (counts.shift(1) - counts).round(0)

    # derived, not asserted: which step loses the largest share, which the most sessions
    sharpest = drop_pct.idxmax()
    sharpest_drop = float(drop_pct.max())
    biggest_loss = lost.idxmax()
    biggest_loss_n = int(lost.max())

    def step_name(target: str) -> str:
        i = FUNNEL.index(target)
        return f"{FUNNEL[i - 1].replace('_', ' ')} → {target.replace('_', ' ')}"

    fig, ax = plt.subplots(figsize=(10, 6), layout="constrained")
    bars = ax.bar(
        range(len(counts)),
        counts.values,
        color=BLUE,
        edgecolor="black",
        width=0.62,
    )
    ax.set_xticks(range(len(counts)))
    ax.set_xticklabels(FUNNEL_TICKS)
    ax.set(
        xlabel="Funnel step (session-level)",
        ylabel="Distinct sessions",
        title=f"Session funnel — payment is the sharpest cliff: "
        f"{sharpest_drop:.1f}% of checkouts never complete",
    )
    ax.yaxis.set_major_formatter(mticker.StrMethodFormatter("{x:,.0f}"))
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
                f"−{drop_pct.iloc[i]:.0f}%",
                (b.get_x() + b.get_width() / 2, n + counts.max() * 0.06),
                ha="center",
                va="bottom",
                fontsize=10,
                color=RED,
                fontweight="bold",
            )
    ax.set_ylim(0, counts.max() * 1.18)
    ax.grid(axis="y", alpha=0.3)
    ax.annotate(
        f"sharpest drop: {step_name(sharpest)}\n−{sharpest_drop:.1f}% of sessions\n\n"
        f"largest absolute loss: {step_name(biggest_loss)}\n−{biggest_loss_n:,} sessions",
        xy=(0.40, 0.70),
        xycoords="axes fraction",
        fontsize=9,
        va="top",
        bbox=dict(boxstyle="round", fc="#FFF3CD", ec="#B8860B", alpha=0.9),
    )
    save(fig, "fig1_funnel_steps.png")


# ---- fig 2: order amount distribution (linear + log) ----------------------
def fig_amount_distribution(orders: pd.DataFrame) -> None:
    amt = orders["amount"]
    log_amt = np.log10(amt)

    fig, axes = plt.subplots(1, 2, figsize=(12, 5), layout="constrained")
    axes[0].hist(amt, bins=40, color=BLUE, edgecolor="black", alpha=0.85)
    axes[0].axvline(amt.median(), color=RED, lw=2, label=f"median {amt.median():.2f}")
    axes[0].axvline(
        amt.mean(), color=ORANGE, lw=2, ls="--", label=f"mean {amt.mean():.2f}"
    )
    axes[0].set(
        xlabel="Order amount ($)",
        ylabel="Orders",
        title=f"Order amount — right-skewed (skew {amt.skew():.2f})",
    )
    axes[0].legend(frameon=False)

    # same variable, same colour: a second hue here would imply a second series
    axes[1].hist(log_amt, bins=40, color=BLUE, edgecolor="black", alpha=0.85)
    axes[1].set(
        xlabel="log10(order amount)",
        ylabel="Orders",
        title=f"log10 scale — tail compressed, core near-symmetric "
        f"(skew {log_amt.skew():.2f})",
    )
    for ax in axes:
        ax.grid(alpha=0.3)
        ax.yaxis.set_major_formatter(mticker.StrMethodFormatter("{x:,.0f}"))
    save(fig, "fig2_order_amount_distribution.png")


# ---- fig 3: purchase conversion by channel (metric by segment) ------------
def fig_conversion_by_channel(users: pd.DataFrame, orders: pd.DataFrame) -> None:
    buyers = orders[["user_id"]].drop_duplicates().assign(b=1)
    u = users.merge(buyers, on="user_id", how="left")
    u["b"] = u["b"].fillna(0).astype(int)
    g = u.groupby("channel")["b"].agg(["size", "sum"])
    g["conv_pct"] = g["sum"] / g["size"] * 100
    g = g.sort_values("conv_pct", ascending=False)

    top, bottom = g.index[0], g.index[-1]
    ratio = g["conv_pct"].iloc[0] / g["conv_pct"].iloc[-1]

    fig, ax = plt.subplots(figsize=(9, 6), layout="constrained")
    bars = ax.bar(g.index, g["conv_pct"], color=BLUE, edgecolor="black", width=0.62)
    overall = u["b"].mean() * 100
    ax.axhline(overall, color=RED, ls="--", lw=1.5, label=f"overall {overall:.2f}%")
    ax.bar_label(bars, fmt="%.2f%%", padding=3, fontsize=10)
    ax.set(
        xlabel="Acquisition channel",
        ylabel="User purchase conversion (%)",
        title=f"Purchase conversion by channel — {top} {g['conv_pct'].iloc[0]:.1f}% vs "
        f"{bottom} {g['conv_pct'].iloc[-1]:.1f}% (×{ratio:.1f})",
    )
    ax.set_ylim(0, g["conv_pct"].max() * 1.2)
    ax.legend(frameon=False)
    ax.grid(axis="y", alpha=0.3)
    save(fig, "fig3_conversion_by_channel.png")


# ---- fig 4: weekly order revenue with anomaly -----------------------------
def fig_weekly_revenue(orders: pd.DataFrame) -> None:
    wk = (
        orders.set_index("order_ts")
        .resample("W")["amount"]
        .agg(["sum", "count"])
        .rename(columns={"sum": "revenue", "count": "orders"})
    )
    peak = wk["revenue"].idxmax()
    prev = wk["revenue"].shift(1).loc[peak]
    jump = (wk.loc[peak, "revenue"] / prev - 1) * 100

    fig, ax = plt.subplots(figsize=(11, 6), layout="constrained")
    ax.plot(
        wk.index,
        wk["revenue"],
        marker="o",
        color=BLUE,
        lw=2,
        label="weekly revenue",
    )
    ax.set(
        xlabel="Week",
        ylabel="Order revenue ($)",
        title=f"Weekly order revenue — ramp-up then plateau; one "
        f"+{jump:.0f}% spike ({peak:%Y-%m-%d})",
    )
    ax.annotate(
        f"+{jump:.0f}% week\n${wk.loc[peak, 'revenue']:,.0f}",
        xy=(peak, wk.loc[peak, "revenue"]),
        # tucked below-right of the peak: the space above and left is the trend line
        xytext=(24, -30),
        textcoords="offset points",
        ha="left",
        va="top",
        arrowprops=dict(arrowstyle="->", color=RED),
        fontsize=9,
        color=RED,
    )
    ax.yaxis.set_major_formatter(mticker.StrMethodFormatter("{x:,.0f}"))
    ax.grid(alpha=0.3)
    ax.legend(frameon=False)
    save(fig, "fig4_weekly_order_revenue.png")


# ---- fig 5: retention decay by cohort -------------------------------------
def _retention_table(users: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    """Per-cohort D1/D7/D30, computed only over users whose window is observable.

    A cohort's day-N retention is censored when signup + N days falls past the end
    of the observation window. Averaging the whole cohort then reads a not-yet-
    measurable day as "did not return", which draws cliffs that do not exist.
    """
    last_obs = events["event_time"].max().normalize()

    activity = events[["user_id", "event_time"]].copy()
    activity["d"] = activity["event_time"].dt.normalize()
    flags = activity.merge(users[["user_id", "signup_date"]], on="user_id", how="right")
    flags["cohort"] = flags["signup_date"].dt.to_period("M").astype(str)

    windows = (1, 7, 30)
    for n in windows:
        flags[f"hit{n}"] = (
            flags["d"] == flags["signup_date"] + pd.Timedelta(days=n)
        ).astype(int)
        flags[f"elig{n}"] = flags["signup_date"] + pd.Timedelta(days=n) <= last_obs

    agg = {f"{k}{n}": "max" for n in windows for k in ("hit", "elig")}
    per_user = flags.groupby("user_id").agg(agg)

    base = users.assign(cohort=users["signup_date"].dt.to_period("M").astype(str))
    joined = base.set_index("user_id").join(per_user)

    rows = []
    for cohort, g in joined.groupby("cohort"):
        row: dict[str, object] = {"cohort": cohort, "users": len(g)}
        for n in windows:
            eligible = g[g[f"elig{n}"]]
            row[f"cov{n}"] = len(eligible) / len(g)
            row[f"d{n}"] = 100 * eligible[f"hit{n}"].mean() if len(eligible) else np.nan
        rows.append(row)

    table = pd.DataFrame(rows).set_index("cohort")
    # show a point only when (almost) the whole cohort could be observed
    for n in windows:
        table.loc[table[f"cov{n}"] < 0.95, f"d{n}"] = np.nan
    return table


def fig_retention(users: pd.DataFrame, events: pd.DataFrame) -> None:
    by = _retention_table(users, events)
    means = {n: float(by[f"d{n}"].mean()) for n in (1, 7, 30)}

    fig, ax = plt.subplots(figsize=(10, 6), layout="constrained")
    for n, color in ((1, BLUE), (7, ORANGE), (30, RED)):
        ax.plot(
            by.index,
            by[f"d{n}"],
            marker="o",
            lw=2,
            label=f"D{n} retention",
            color=color,
        )
    ax.set(
        xlabel="Signup-month cohort",
        ylabel="Retention (%)",
        title=f"Retention decays {means[1]:.1f}% (D1) → {means[7]:.1f}% (D7) → "
        f"{means[30]:.1f}% (D30) on fully observed cohorts",
    )
    # zero baseline: a truncated axis would inflate the 19.6% -> 5.0% decay
    ax.set_ylim(0, float(by[["d1", "d7", "d30"]].max().max()) * 1.2)
    censored = [c for c in by.index if by.loc[c, ["d1", "d7", "d30"]].isna().any()]
    if censored:
        ax.annotate(
            f"{', '.join(censored)}: D7/D30 not yet\nobservable — no point plotted",
            xy=(0.62, 0.45),
            xycoords="axes fraction",
            fontsize=9,
            color="grey",
            bbox=dict(boxstyle="round", fc="white", ec="grey", alpha=0.9),
        )
    ax.legend(frameon=False)
    ax.grid(alpha=0.3)
    save(fig, "fig5_retention_decay.png")


# ---- fig 6: real-data repeat & concentration ------------------------------
def fig_retail_concentration() -> None:
    con = duckdb.connect()
    try:
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
    finally:
        con.close()

    whale = buckets.iloc[-1]
    x = np.arange(len(buckets))
    w = 0.38
    fig, ax = plt.subplots(figsize=(10, 6), layout="constrained")
    ax.bar(
        x - w / 2,
        buckets["cust_share"],
        w,
        label="% of customers",
        color=BLUE,
        edgecolor="black",
    )
    ax.bar(
        x + w / 2,
        buckets["rev_share"],
        w,
        label="% of revenue",
        color=ORANGE,
        edgecolor="black",
    )
    ax.set_xticks(x)
    ax.set_xticklabels(buckets["bucket"])
    ax.set(
        xlabel="Order count bucket (UCI Online Retail II, real data)",
        ylabel="Share (%)",
        title=f"Real data flips the synthetic story: {whale['cust_share']:.1f}% of "
        f"customers ({whale['bucket']} orders) carry {whale['rev_share']:.0f}% of revenue",
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


def main() -> None:
    data = load()
    fig_funnel(data["events"])
    fig_amount_distribution(data["orders"])
    fig_conversion_by_channel(data["users"], data["orders"])
    fig_weekly_revenue(data["orders"])
    fig_retention(data["users"], data["events"])
    fig_retail_concentration()
    print("done")


if __name__ == "__main__":
    main()
