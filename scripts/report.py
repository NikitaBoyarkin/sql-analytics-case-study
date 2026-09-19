"""Generate a self-contained portfolio report for all SQL cases.

Runs every case in cases/ against data/analytics.duckdb, renders a
dark-themed matplotlib chart per case, and assembles a single HTML file
with embedded base64 PNGs (no external assets, shareable as one file).

Usage:
    uv run python scripts/report.py                    # -> reports/index.html
    uv run python scripts/report.py --out reports/r.html
"""

from __future__ import annotations

import argparse
import base64
import io
import pathlib
from html import escape

import duckdb
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).parent.parent
CASES = ROOT / "cases"
DB = ROOT / "data" / "analytics.duckdb"

BG = "#0f172a"
PANEL = "#1e293b"
GRID = "#334155"
TXT = "#e2e8f0"
ACCENT = "#38bdf8"
ACCENT2 = "#34d399"
ACCENT3 = "#f472b6"
ACCENT4 = "#fbbf24"

# Per-case display metadata: title + the business signal the result reveals.
META: dict[int, dict] = {
    1: {
        "title": "Funnel conversion",
        "signal": "The sharpest drop is add-to-cart -> checkout (54% of carts never "
        "proceed). That is the highest-leverage step to instrument and fix.",
    },
    2: {
        "title": "N-day retention by cohort",
        "signal": "D1 ~19-21% collapses to D30 ~5%. The D1->D7 drop points at the "
        "onboarding window as the retention bottleneck, not long-term engagement.",
    },
    3: {
        "title": "Rolling 30-day retention",
        "signal": "Windowed retention is a fairer lens for sporadic-use products — it does "
        "not punish users who return a few days late.",
    },
    4: {
        "title": "DAU / MAU / stickiness",
        "signal": "Stickiness is a frequency metric, not reach. ~40% means the average "
        "user is active ~12 days/month.",
    },
    5: {
        "title": "LTV by cohort",
        "signal": "Cohort LTV must be compared at the same age, not calendar date — younger "
        "cohorts look smaller simply because they have had less time to spend.",
    },
    6: {
        "title": "Top-3 categories per country",
        "signal": "Use ROW_NUMBER (not RANK/DENSE_RANK) when you want exactly N rows per "
        "group regardless of ties.",
    },
    7: {
        "title": "Cumulative revenue",
        "signal": "ROWS UNBOUNDED PRECEDING is the safe default for running totals when "
        "order dates can repeat; RANGE would merge duplicate days.",
    },
    8: {
        "title": "Longest active-day streak",
        "signal": "The day - row_number trick is the canonical gaps-and-islands pattern: it "
        "converts 'consecutive' into 'same group' in one pass.",
    },
    9: {
        "title": "A/B conversion by variant (with significance)",
        "signal": "Treatment converts higher and the lift is statistically significant "
        "(z=4.8, p<0.01). Note the unit: user-level conversion (~4-5%) is far "
        "higher than session-level (~1%, case 01) — pick the unit before reporting.",
    },
    10: {
        "title": "Revenue attribution: lifetime vs first-touch",
        "signal": "The gap between first-touch and lifetime revenue is itself a signal — "
        "large gaps mark channels with repeat-purchase potential worth investing in.",
    },
    11: {
        "title": "7-day moving average of DAU",
        "signal": "The MA smooths weekly noise and shows steady growth to a ~460 DAU "
        "plateau. The flat end is saturation, not a data artifact — sessions "
        "are right-truncated, not clamped to the last day.",
    },
    12: {
        "title": "Top-2 revenue users per country (QUALIFY)",
        "signal": "QUALIFY filters after window functions but before SELECT — a modern "
        "DuckDB idiom that removes a wrapping subquery.",
    },
    13: {
        "title": "Monthly revenue by category (PIVOT)",
        "signal": "Revenue mix shifts month to month; June is up across every category. "
        "PIVOT turns long-form revenue into a readable category-by-month matrix.",
    },
    14: {
        "title": "Subscription MRR (recursive CTE)",
        "signal": "MRR grows ~15x Jan->Jun (169 -> 2500) as subscriptions compound. A "
        "recursive CTE expands each sub into one row per billing month — annual "
        "plans recognized as ARR/12.",
    },
    15: {
        "title": "Order amount distribution (median/p90/p99)",
        "signal": "Medians sit at $21-25 but p99 reaches $63-93 — a fat tail. A p99 AOV "
        "guard catches outliers; median (not mean) is the honest central AOV.",
    },
    16: {
        "title": "Sessionization & session depth",
        "signal": "A 30-min inactivity gap reconstructs the 80k pre-assigned sessions "
        "with 99.6% fidelity (298 sub-30-min same-day sessions merged, none split). "
        "Median session = 2 events — depth, not duration, is the engagement signal.",
    },
    17: {
        "title": "Weekly lifecycle composition",
        "signal": "New users fall from 100% to ~30% of the weekly base while resurrecting "
        "grows to ~33% and dormant climbs to ~60% of active — reactivation does as "
        "much work as acquisition.",
    },
    18: {
        "title": "Cohort revenue retention (triangle)",
        "signal": "Revenue retention holds at ~67-88% into month 1 but collapses to "
        "~10-20% by month 2 — one purchase is effectively lifetime. Monetization has "
        "no repeat engine.",
    },
    19: {
        "title": "Repeat purchase & time between orders",
        "signal": "Only 3.5% of buyers ever return (896 buyers, 31 repeat). This is a "
        "one-and-done purchase engine — the repeat lever is the biggest monetization gap.",
    },
    20: {
        "title": "RFM segmentation (NTILE)",
        "signal": "Revenue splits ~evenly across segments; Big Spenders are just 1.2%. The "
        "frequency axis barely discriminates because repeat rate is 3.5% — RFM here is "
        "mostly a recency story.",
    },
    21: {
        "title": "Subscription churn (logo & MRR)",
        "signal": "Logo churn grows from 5.6% to ~15% as the base matures; MRR churn tracks "
        "it. MRR compounding (case 14) is hiding a fast-leaking bucket — a churn alarm.",
    },
    22: {
        "title": "Refunds & net revenue",
        "signal": "~4.1% of gross is refunded (2.2-6.0%/month, February worst). Report net, "
        "not gross — refund rate is a revenue-quality number.",
    },
    23: {
        "title": "Pareto revenue concentration",
        "signal": "Top decile = 22.3% of revenue, top 3 deciles = 50.2%. No 80/20 — there "
        "is no whale tier, so don't build a VIP product for one.",
    },
    24: {
        "title": "Daily revenue anomaly detection",
        "signal": "Median+MAD z-score on a trailing-14-day baseline flags exactly 4 days "
        "(Jan 25 z=5.3, Mar 23, Apr 7, Jun 14) — a promo pattern to investigate, not noise.",
    },
    25: {
        "title": "Purchase → subscription conversion",
        "signal": "29.9% of purchasers subscribe within a week (median 3 days, p90 6); 26% "
        "pick annual. The upsell window is narrow — hit it fast.",
    },
    26: {
        "title": "Real data — repeat purchase & concentration",
        "signal": "On the real UCI Online Retail II data the pattern inverts: 72.4% of "
        "customers repeat and the top 15% (11+ orders) drive 65% of revenue, while "
        "one-time buyers are 28% of customers but 3% of revenue. Same SQL, opposite "
        "business conclusion — the synthetic engine is a one-and-done anomaly.",
    },
}


def run_case(con: duckdb.DuckDBPyConnection, path: pathlib.Path) -> pd.DataFrame:
    return con.execute(path.read_text()).fetchdf()


def question_and_approach(sql: str) -> tuple[str, str]:
    """Extract 'Question' and 'Approach' lines from the leading comment block."""
    q, a = "", ""
    for line in sql.splitlines():
        if not line.startswith("--"):
            break
        text = line.lstrip("- ").strip()
        if text.lower().startswith("question:"):
            q = text.split(":", 1)[1].strip()
        elif text.lower().startswith("approach:"):
            a = text.split(":", 1)[1].strip()
    return q, a


def _style(ax) -> None:
    ax.set_facecolor(PANEL)
    ax.tick_params(colors=TXT, labelsize=8)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.xaxis.label.set_color(TXT)
    ax.yaxis.label.set_color(TXT)
    ax.title.set_color(TXT)
    ax.grid(axis="y", color=GRID, alpha=0.4, linewidth=0.6)


def _fig(w=8, h=3.4):
    fig, ax = plt.subplots(figsize=(w, h), dpi=130)
    fig.patch.set_facecolor(BG)
    return fig, ax


def _b64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode()


# --- per-case chart builders -------------------------------------------------


def chart_01(df: pd.DataFrame) -> str:
    fig, ax = _fig()
    names = df["event_name"].tolist()[::-1]
    vals = df["sessions"].astype(int).tolist()[::-1]
    colors = [ACCENT if i == 0 else "#334155" for i in range(len(vals))]
    ax.barh(names, vals, color=colors)
    for i, v in enumerate(vals):
        ax.text(v + 500, i, f"{v:,}", va="center", color=TXT, fontsize=8)
    ax.set_xlabel("sessions reaching step")
    _style(ax)
    return _b64(fig)


def chart_02(df: pd.DataFrame) -> str:
    fig, ax = _fig()
    x = np.arange(len(df))
    w = 0.26
    for i, (col, c) in enumerate(
        [
            ("d1_retention", ACCENT),
            ("d7_retention", ACCENT2),
            ("d30_retention", ACCENT3),
        ]
    ):
        ax.bar(x + (i - 1) * w, df[col], w, color=c, label=col.split("_")[0])
    ax.set_xticks(
        x, [str(m)[:7] for m in df["cohort"]], rotation=30, ha="right", fontsize=7
    )
    ax.set_ylabel("retention %")
    ax.legend(fontsize=7, facecolor=PANEL, labelcolor=TXT)
    _style(ax)
    return _b64(fig)


def chart_03(df: pd.DataFrame) -> str:
    fig, ax = _fig()
    for col, c in [
        ("win_7d", ACCENT),
        ("win_14d", ACCENT2),
        ("win_30d", ACCENT3),
        ("win_60d", ACCENT4),
    ]:
        ax.plot(df["cohort"].astype(str), df[col], marker="o", ms=3, color=c, label=col)
    ax.set_ylabel("retention %")
    ax.legend(fontsize=7, facecolor=PANEL, labelcolor=TXT)
    _style(ax)
    return _b64(fig)


def chart_04(df: pd.DataFrame) -> str:
    fig, ax = _fig()
    ax.plot(df["d"], df["dau"], color=ACCENT, label="DAU", lw=1.2)
    ax.plot(df["d"], df["mau"], color=ACCENT2, label="MAU (28d)", lw=1.2)
    ax.set_ylabel("active users")
    ax.legend(loc="upper left", fontsize=7, facecolor=PANEL, labelcolor=TXT)
    ax2 = ax.twinx()
    ax2.plot(df["d"], df["stickiness_pct"], color=ACCENT3, lw=1.0, label="stickiness %")
    ax2.set_ylabel("stickiness %", color=ACCENT3)
    ax2.tick_params(colors=ACCENT3, labelsize=8)
    _style(ax)
    return _b64(fig)


def chart_05(df: pd.DataFrame) -> str:
    fig, ax = _fig()
    ax.bar([str(m)[:7] for m in df["cohort"]], df["ltv_per_user"], color=ACCENT)
    for i, v in enumerate(df["ltv_per_user"]):
        ax.text(i, v + 0.02, f"{v:.2f}", ha="center", color=TXT, fontsize=8)
    ax.set_ylabel("LTV per user ($)")
    _style(ax)
    return _b64(fig)


def chart_06(df: pd.DataFrame) -> str:
    fig, ax = _fig(w=8.5)
    piv = df.pivot(index="country", columns="rnk", values="revenue").sort_index()
    piv.plot(kind="bar", ax=ax, color=[ACCENT, ACCENT2, ACCENT4], legend=False)
    ax.set_ylabel("revenue ($)")
    for i, c in enumerate(piv.index):
        for j in range(piv.shape[1]):
            v = piv.iloc[i, j]
            if pd.notna(v):
                ax.text(
                    i + (j - 1) * 0.25,
                    v + 5,
                    f"{v:.0f}",
                    ha="center",
                    fontsize=6,
                    color=TXT,
                )
    ax.set_xticklabels(piv.index, rotation=0, fontsize=8)
    _style(ax)
    return _b64(fig)


def chart_07(df: pd.DataFrame) -> str:
    fig, ax = _fig()
    ax.fill_between(df["d"], df["cumulative"], color=ACCENT, alpha=0.35)
    ax.plot(df["d"], df["cumulative"], color=ACCENT, lw=1.4)
    ax.set_ylabel("cumulative revenue ($)")
    ax2 = ax.twinx()
    ax2.bar(
        df["d"], df["daily_revenue"], color=ACCENT3, width=0.8, alpha=0.5, label="daily"
    )
    ax2.set_ylabel("daily revenue ($)", color=ACCENT3)
    ax2.tick_params(colors=ACCENT3, labelsize=8)
    _style(ax)
    return _b64(fig)


def chart_08(df: pd.DataFrame) -> str:
    fig, ax = _fig(w=7)
    ax.barh(df["user_id"].astype(str), df["longest_streak_days"], color=ACCENT)
    ax.set_xlabel("longest active-day streak")
    _style(ax)
    return _b64(fig)


def chart_09(df: pd.DataFrame) -> str:
    fig, ax = _fig()
    row = df.sort_values("ab_variant").iloc[0]
    lift = row["lift_pp"]
    p = row["p_value"]
    ax.bar(df["ab_variant"], df["conv_pct"], color=[ACCENT2, ACCENT3])
    for i, v in enumerate(df["conv_pct"]):
        ax.text(i, v + 0.05, f"{v:.2f}%", ha="center", color=TXT, fontsize=9)
    ax.set_ylabel("purchase conversion %")
    ax.set_title(
        f"lift = {lift:+.2f}pp   |   z = {row['z_score']:.2f}   |   p = {p:.6f}",
        fontsize=9,
        color=ACCENT,
    )
    _style(ax)
    return _b64(fig)


def chart_10(df: pd.DataFrame) -> str:
    fig, ax = _fig()
    x = np.arange(len(df))
    ax.bar(x - 0.18, df["lifetime_revenue"], 0.36, color=ACCENT, label="lifetime")
    ax.bar(
        x + 0.18, df["first_touch_revenue"], 0.36, color=ACCENT3, label="first-touch"
    )
    ax.set_xticks(x, df["channel"], fontsize=8)
    ax.set_ylabel("revenue ($)")
    ax.legend(fontsize=7, facecolor=PANEL, labelcolor=TXT)
    _style(ax)
    return _b64(fig)


def chart_11(df: pd.DataFrame) -> str:
    fig, ax = _fig()
    ax.plot(df["d"], df["dau"], color="#475569", lw=0.7, alpha=0.8, label="DAU")
    ax.plot(df["d"], df["dau_ma7"], color=ACCENT, lw=1.6, label="DAU 7d MA")
    ax.set_ylabel("active users")
    ax.legend(fontsize=7, facecolor=PANEL, labelcolor=TXT)
    _style(ax)
    return _b64(fig)


def chart_12(df: pd.DataFrame) -> str:
    fig, ax = _fig(w=8)
    piv = df.pivot(index="country", columns="user_id", values="revenue")
    piv.plot(kind="bar", ax=ax, legend=False, color=[ACCENT, ACCENT3])
    ax.set_ylabel("revenue ($)")
    ax.set_xticklabels(piv.index, rotation=0, fontsize=8)
    _style(ax)
    return _b64(fig)


def chart_13(df: pd.DataFrame) -> str:
    fig, ax = _fig(w=8)
    cats = [c for c in df.columns if c != "month"]
    x = np.arange(len(df))
    colors = [ACCENT, ACCENT2, ACCENT3, ACCENT4, "#a78bfa", "#f97316"]
    for i, c in enumerate(cats):
        ax.bar(
            x + (i - len(cats) / 2 + 0.5) * 0.13, df[c], 0.13, color=colors[i], label=c
        )
    ax.set_xticks(
        x, [str(m)[:7] for m in df["month"]], rotation=30, ha="right", fontsize=7
    )
    ax.set_ylabel("revenue ($)")
    ax.legend(fontsize=6, ncol=3, facecolor=PANEL, labelcolor=TXT)
    _style(ax)
    return _b64(fig)


def chart_14(df: pd.DataFrame) -> str:
    fig, ax = _fig()
    ax.fill_between(df["month"], df["mrr"], color=ACCENT, alpha=0.35)
    ax.plot(df["month"], df["mrr"], color=ACCENT, marker="o", ms=3, lw=1.5)
    for _, r in df.iterrows():
        ax.text(
            r["month"],
            r["mrr"] + 60,
            f"{r['mrr']:.0f}",
            ha="center",
            fontsize=7,
            color=TXT,
        )
    ax.set_ylabel("MRR ($)")
    _style(ax)
    return _b64(fig)


def chart_15(df: pd.DataFrame) -> str:
    fig, ax = _fig(w=8)
    x = np.arange(len(df))
    w = 0.26
    for i, (col, c) in enumerate(
        [("median_amount", ACCENT), ("p90", ACCENT3), ("p99", ACCENT4)]
    ):
        ax.bar(x + (i - 1) * w, df[col], w, color=c, label=col.replace("_amount", ""))
    ax.set_xticks(x, df["product_category"], fontsize=7)
    ax.set_ylabel("amount ($)")
    ax.legend(fontsize=7, facecolor=PANEL, labelcolor=TXT)
    _style(ax)
    return _b64(fig)


def chart_16(df: pd.DataFrame) -> str:
    fig, ax = _fig(w=7.5)
    order = [
        "sessions_1_event",
        "sessions_2_3_events",
        "sessions_4_5_events",
        "sessions_6plus_events",
    ]
    labels = {
        "sessions_1_event": "1 event",
        "sessions_2_3_events": "2-3 events",
        "sessions_4_5_events": "4-5 events",
        "sessions_6plus_events": "6+ events",
    }
    sub = df[df["metric"].isin(order)].set_index("metric").reindex(order)
    vals = sub["value"].astype(int)
    ax.bar([labels[m] for m in sub.index], vals, color=ACCENT)
    for i, v in enumerate(vals):
        ax.text(i, v + 500, f"{v:,}", ha="center", color=TXT, fontsize=8)
    ax.set_ylabel("derived sessions")
    _style(ax)
    return _b64(fig)


def chart_17(df: pd.DataFrame) -> str:
    fig, ax = _fig(w=9, h=3.6)
    weeks = [str(w)[:10] for w in df["wk"]]
    ax.bar(weeks, df["new_users"], color=ACCENT, label="new")
    ax.bar(
        weeks,
        df["returning_users"],
        bottom=df["new_users"],
        color=ACCENT2,
        label="returning",
    )
    ax.bar(
        weeks,
        df["resurrecting_users"],
        bottom=df["new_users"] + df["returning_users"],
        color=ACCENT3,
        label="resurrecting",
    )
    ax.plot(
        weeks,
        df["dormant_users"],
        color=ACCENT4,
        marker="o",
        ms=2,
        lw=1.0,
        label="dormant",
    )
    ticks = list(range(0, len(weeks), 4))
    ax.set_xticks(ticks)
    ax.set_xticklabels([weeks[i] for i in ticks], fontsize=7)
    ax.set_ylabel("users")
    ax.legend(fontsize=6, facecolor=PANEL, labelcolor=TXT)
    _style(ax)
    return _b64(fig)


def chart_18(df: pd.DataFrame) -> str:
    fig, ax = _fig(w=7, h=4.2)
    piv = df.pivot(index="cohort", columns="period", values="revenue")
    mat = piv.fillna(0).values
    ax.imshow(mat, aspect="auto", cmap="Blues")
    ax.set_xticks(range(piv.shape[1]))
    ax.set_xticklabels([f"m{c}" for c in piv.columns], fontsize=7)
    ax.set_yticks(range(piv.shape[0]))
    ax.set_yticklabels([str(c)[:7] for c in piv.index], fontsize=7)
    for i in range(piv.shape[0]):
        for j in range(piv.shape[1]):
            v = mat[i, j]
            if v > 0:
                ax.text(
                    j,
                    i,
                    f"{v:.0f}",
                    ha="center",
                    va="center",
                    fontsize=7,
                    color="white" if v > mat.max() * 0.5 else "#0f172a",
                )
    ax.set_xlabel("months since signup")
    ax.set_title("revenue per cohort-period ($)", fontsize=9, color=TXT)
    ax.grid(False)
    for s in ("top", "right", "left", "bottom"):
        ax.spines[s].set_visible(False)
    ax.tick_params(colors=TXT, labelsize=8)
    return _b64(fig)


def chart_19(df: pd.DataFrame) -> str:
    fig, ax = _fig(w=7)
    order = [
        "buyers_1_order",
        "buyers_2_orders",
        "buyers_3_orders",
        "buyers_4plus_orders",
    ]
    labels = {
        "buyers_1_order": "1 order",
        "buyers_2_orders": "2 orders",
        "buyers_3_orders": "3 orders",
        "buyers_4plus_orders": "4+ orders",
    }
    sub = df[df["metric"].isin(order)].set_index("metric").reindex(order)
    vals = sub["value"].astype(int)
    ax.bar(
        [labels[m] for m in sub.index], vals, color=[ACCENT, ACCENT2, ACCENT3, ACCENT4]
    )
    for i, v in enumerate(vals):
        ax.text(i, v + 5, str(v), ha="center", color=TXT, fontsize=8)
    ax.set_ylabel("buyers")
    _style(ax)
    return _b64(fig)


def chart_20(df: pd.DataFrame) -> str:
    fig, ax = _fig(w=8)
    d = df.sort_values("revenue", ascending=False)
    ax.bar(d["segment"], d["revenue"], color=ACCENT)
    for i, (rev, pct) in enumerate(zip(d["revenue"], d["pct_of_revenue"])):
        ax.text(
            i, rev + 40, f"{rev:.0f} ({pct:.0f}%)", ha="center", color=TXT, fontsize=7
        )
    ax.set_ylabel("revenue ($)")
    ax.tick_params(axis="x", labelsize=7)
    _style(ax)
    return _b64(fig)


def chart_21(df: pd.DataFrame) -> str:
    fig, ax = _fig(w=7)
    ax.plot(
        df["m"],
        df["logo_churn_pct"],
        marker="o",
        ms=3,
        color=ACCENT,
        label="logo churn %",
    )
    ax.plot(
        df["m"],
        df["mrr_churn_pct"],
        marker="o",
        ms=3,
        color=ACCENT3,
        label="MRR churn %",
    )
    ax.set_xticks(
        range(len(df)),
        [str(m)[:7] for m in df["m"]],
        fontsize=7,
        rotation=30,
        ha="right",
    )
    ax.set_ylabel("churn %")
    ax.legend(fontsize=7, facecolor=PANEL, labelcolor=TXT)
    _style(ax)
    return _b64(fig)


def chart_22(df: pd.DataFrame) -> str:
    fig, ax = _fig(w=8)
    x = np.arange(len(df))
    w = 0.36
    ax.bar(x - w / 2, df["gross"], w, color=ACCENT, label="gross")
    ax.bar(x + w / 2, df["net"], w, color=ACCENT2, label="net")
    for i, (g, n) in enumerate(zip(df["gross"], df["net"])):
        ax.text(i - w / 2, g + 20, f"{g:.0f}", ha="center", fontsize=7, color=TXT)
        ax.text(i + w / 2, n + 20, f"{n:.0f}", ha="center", fontsize=7, color=TXT)
    ax.set_xticks(x, [str(m)[:7] for m in df["m"]], fontsize=7, rotation=30, ha="right")
    ax.set_ylabel("revenue ($)")
    ax.legend(fontsize=7, facecolor=PANEL, labelcolor=TXT)
    _style(ax)
    return _b64(fig)


def chart_23(df: pd.DataFrame) -> str:
    fig, ax = _fig(w=7.5)
    ax.bar(
        df["decile"],
        df["pct_of_revenue"],
        color=ACCENT,
        alpha=0.85,
        label="% of revenue",
    )
    ax.plot(
        df["decile"],
        df["cum_pct"],
        color=ACCENT3,
        marker="o",
        ms=3,
        lw=1.4,
        label="cumulative %",
    )
    for i, c in enumerate(df["cum_pct"]):
        ax.text(
            i,
            df["pct_of_revenue"].iloc[i] + 0.5,
            f"{c:.0f}%",
            ha="center",
            fontsize=7,
            color=TXT,
        )
    ax.set_xticks(df["decile"])
    ax.set_ylabel("% of revenue")
    ax.legend(fontsize=7, facecolor=PANEL, labelcolor=TXT)
    _style(ax)
    return _b64(fig)


def chart_24(df: pd.DataFrame) -> str:
    fig, ax = _fig(w=9, h=3.6)
    ax.plot(
        df["d"],
        df["daily_revenue"],
        color="#475569",
        lw=0.7,
        alpha=0.9,
        label="daily revenue",
    )
    ax.plot(
        df["d"],
        df["baseline_median"],
        color=ACCENT,
        lw=1.2,
        label="14d median baseline",
    )
    an = df[df["anomalous"] == "YES"]
    ax.scatter(
        an["d"], an["daily_revenue"], color=ACCENT3, s=30, zorder=5, label="anomalous"
    )
    ax.set_ylabel("revenue ($)")
    ax.legend(fontsize=7, facecolor=PANEL, labelcolor=TXT)
    _style(ax)
    return _b64(fig)


def chart_25(df: pd.DataFrame) -> str:
    fig, ax = _fig(w=6)
    s = {m: v for m, v in zip(df["metric"], df["value"])}
    labels = ["monthly", "annual"]
    vals = [int(s["monthly_subs"]), int(s["annual_subs"])]
    ax.bar(labels, vals, color=[ACCENT, ACCENT3])
    for i, v in enumerate(vals):
        ax.text(i, v + 4, str(v), ha="center", color=TXT, fontsize=9)
    ax.set_ylabel("converted users")
    _style(ax)
    return _b64(fig)


def chart_26(df: pd.DataFrame) -> str:
    fig, ax = _fig(w=8)
    x = np.arange(len(df))
    w = 0.38
    ax.bar(
        x - w / 2, df["customer_share_pct"], w, color=ACCENT2, label="% of customers"
    )
    ax.bar(x + w / 2, df["revenue_share_pct"], w, color=ACCENT, label="% of revenue")
    for i in range(len(df)):
        ax.text(
            i - w / 2,
            df["customer_share_pct"].iloc[i] + 1,
            f"{df['customer_share_pct'].iloc[i]:.0f}",
            ha="center",
            fontsize=7,
            color=TXT,
        )
        ax.text(
            i + w / 2,
            df["revenue_share_pct"].iloc[i] + 1,
            f"{df['revenue_share_pct'].iloc[i]:.0f}",
            ha="center",
            fontsize=7,
            color=TXT,
        )
    ax.set_xticks(x, df["bucket"])
    ax.set_xlabel("orders per customer")
    ax.set_ylabel("% share")
    ax.legend(fontsize=7, facecolor=PANEL, labelcolor=TXT)
    _style(ax)
    return _b64(fig)


CHARTS = {
    1: chart_01,
    2: chart_02,
    3: chart_03,
    4: chart_04,
    5: chart_05,
    6: chart_06,
    7: chart_07,
    8: chart_08,
    9: chart_09,
    10: chart_10,
    11: chart_11,
    12: chart_12,
    13: chart_13,
    14: chart_14,
    15: chart_15,
    16: chart_16,
    17: chart_17,
    18: chart_18,
    19: chart_19,
    20: chart_20,
    21: chart_21,
    22: chart_22,
    23: chart_23,
    24: chart_24,
    25: chart_25,
    26: chart_26,
}


def df_to_html(df: pd.DataFrame) -> str:
    df = df.copy()
    return df.to_html(index=False, border=0, classes="tbl", escape=False)


def dataset_summary(con: duckdb.DuckDBPyConnection) -> dict[str, int]:
    def count(table: str) -> int:
        try:
            return con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        except duckdb.Error:
            return 0

    return {
        "users": count("users"),
        "events": count("events"),
        "sessions": con.execute(
            "SELECT COUNT(DISTINCT session_id) FROM events"
        ).fetchone()[0],
        "orders": count("orders"),
        "subscriptions": count("subscriptions"),
        "refunds": count("refunds"),
        "cancellations": count("subscription_cancellations"),
        "online_retail": count("online_retail"),
    }


def build_html(con: duckdb.DuckDBPyConnection, cases: list[pathlib.Path]) -> str:
    stats = dataset_summary(con)
    sections = []
    for path in sorted(cases, key=lambda p: int(p.name.split("_")[0])):
        num = int(path.name.split("_")[0])
        sql = path.read_text()
        q, a = question_and_approach(sql)
        df = run_case(con, path)
        img = CHARTS[num](df) if num in CHARTS else None
        meta = META[num]
        chart_html = f'<img src="data:image/png;base64,{img}"/>' if img else ""
        sections.append(f"""
        <section id="case{num}">
          <h2><span class="num">{num:02d}</span> {escape(meta["title"])}</h2>
          <p class="q"><b>Question:</b> {escape(q)}</p>
          <p class="q"><b>Approach:</b> {escape(a)}</p>
          {chart_html}
          {df_to_html(df)}
          <div class="signal"><b>Signal →</b> {escape(meta["signal"])}</div>
        </section>""")

    toc = "".join(
        f'<a href="#case{int(p.name.split("_")[0])}">'
        f"{int(p.name.split('_')[0]):02d} · {META[int(p.name.split('_')[0])]['title']}</a>"
        for p in sorted(cases, key=lambda p: int(p.name.split("_")[0]))
    )

    exec_insights = [
        (
            "Funnel",
            "Biggest drop is add-to-cart → checkout (54% of carts never proceed) — the highest-leverage step to fix.",
        ),
        (
            "Retention",
            "D1 retention is stable at ~19-21% but collapses to ~5% by D30. The onboarding window is the leak, not long-term engagement.",
        ),
        (
            "A/B test",
            "Treatment wins on purchase conversion (4.9% vs 3.8%, +1.1pp) and the result is statistically significant (z=4.8, p<0.01).",
        ),
        (
            "Lifecycle",
            "New users fall from 100% to ~30% of the weekly base while resurrecting grows to ~33% — reactivation does as much work as acquisition.",
        ),
        (
            "Revenue retention",
            "Month-1 revenue retention holds (~67-88%) but month-2 cliffs to ~10-20%; repeat rate is just 3.5% — one purchase ≈ lifetime.",
        ),
        (
            "Subscriptions & churn",
            "MRR compounds ~15x Jan→Jun (case 14) while logo churn reaches ~15%/month "
            "(case 21) — the engine grows even as it leaks; churn is the next lever.",
        ),
        (
            "Real data (case 26)",
            "On the real UCI Online Retail II data the picture inverts: 72.4% of "
            "customers repeat and the top 15% (11+ orders) drive 65% of revenue — "
            "unlike the synthetic one-and-done engine.",
        ),
    ]
    exec_html = "".join(
        f'<div class="kpi"><div class="kpi-t">{t}</div><div class="kpi-v">{v}</div></div>'
        for t, v in exec_insights
    )

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>SQL Analytics Case Study — Report</title>
<style>
  :root {{ color-scheme: dark; }}
  * {{ box-sizing: border-box; }}
  body {{ margin:0; background:{BG}; color:{TXT};
         font-family:-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif; }}
  .wrap {{ max-width:980px; margin:0 auto; padding:32px 20px 80px; }}
  h1 {{ font-size:28px; margin:0 0 4px; }}
  .sub {{ color:#94a3b8; margin:0 0 8px; font-size:14px; }}
  .stats {{ display:flex; flex-wrap:wrap; gap:10px; margin:18px 0 26px; }}
  .stat {{ background:{PANEL}; border:1px solid {GRID}; border-radius:10px;
          padding:10px 16px; min-width:120px; }}
  .stat b {{ font-size:20px; display:block; color:{ACCENT}; }}
  .stat span {{ font-size:11px; color:#94a3b8; }}
  .toc {{ background:{PANEL}; border:1px solid {GRID}; border-radius:10px;
         padding:12px 16px; display:flex; flex-wrap:wrap; gap:6px 14px; font-size:12.5px; }}
  .toc a {{ color:{ACCENT}; text-decoration:none; }}
  .kpis {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:10px;
          margin:22px 0 4px; }}
  .kpi {{ background:{PANEL}; border:1px solid {GRID}; border-radius:10px; padding:12px 14px; }}
  .kpi-t {{ font-size:11px; color:{ACCENT2}; text-transform:uppercase; letter-spacing:.05em; }}
  .kpi-v {{ font-size:12.5px; margin-top:5px; line-height:1.45; }}
  section {{ margin-top:34px; }}
  h2 {{ font-size:20px; margin:0 0 10px; }}
  .num {{ color:{ACCENT4}; font-weight:700; margin-right:6px; }}
  .q {{ font-size:13px; color:#cbd5e1; margin:4px 0; }}
  .q b {{ color:{ACCENT}; }}
  img {{ width:100%; border:1px solid {GRID}; border-radius:10px; margin:12px 0; background:{BG}; }}
  .tbl {{ border-collapse:collapse; width:100%; font-size:12.5px; margin:6px 0; }}
  .tbl th {{ background:{PANEL}; color:{ACCENT}; text-align:left; padding:6px 10px;
            border-bottom:1px solid {GRID}; }}
  .tbl td {{ padding:5px 10px; border-bottom:1px solid #1e293b; font-variant-numeric:tabular-nums; }}
  .tbl tr:nth-child(even) td {{ background:#111c30; }}
  .signal {{ margin-top:12px; background:#0b1c2e; border-left:3px solid {ACCENT};
           padding:10px 14px; font-size:13.5px; border-radius:0 8px 8px 0; }}
  .foot {{ margin-top:48px; color:#64748b; font-size:12px; border-top:1px solid {GRID}; padding-top:14px; }}
</style></head>
<body><div class="wrap">
  <h1>SQL Analytics Case Study</h1>
  <p class="sub">25 synthetic SQL analyses + 1 real-data case (UCI Online Retail II) · DuckDB · deterministic (seed 42)</p>
  <div class="stats">
    <div class="stat"><b>{stats["users"]:,}</b><span>users</span></div>
    <div class="stat"><b>{stats["events"]:,}</b><span>events</span></div>
    <div class="stat"><b>{stats["sessions"]:,}</b><span>sessions</span></div>
    <div class="stat"><b>{stats["orders"]:,}</b><span>orders</span></div>
    <div class="stat"><b>{stats["subscriptions"]:,}</b><span>subscriptions</span></div>
    <div class="stat"><b>{stats["refunds"]:,}</b><span>refunds</span></div>
    <div class="stat"><b>{stats["cancellations"]:,}</b><span>cancellations</span></div>
    <div class="stat"><b>{stats["online_retail"]:,}</b><span>real invoice lines</span></div>
  </div>
  <nav class="toc">{toc}</nav>
  <div class="kpis">{exec_html}</div>
  {"".join(sections)}
  <p class="foot">Generated from {len(cases)} SQL cases against data/analytics.duckdb ·
  Reproduce: <code>uv run python data/generate_data.py</code> then
  <code>uv run python scripts/report.py</code>.</p>
</div></body></html>"""


def main() -> None:
    ap = argparse.ArgumentParser(description="Render the SQL case-study report.")
    ap.add_argument("--out", default=str(ROOT / "reports" / "index.html"))
    args = ap.parse_args()

    if not DB.exists():
        raise SystemExit("Database missing. Run: uv run python data/generate_data.py")
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect(str(DB), read_only=True)
    try:
        cases = sorted(CASES.glob("*.sql"), key=lambda p: int(p.name.split("_")[0]))
        html = build_html(con, cases)
    finally:
        con.close()
    out.write_text(html)
    print(f"Wrote report: {out} ({len(html) / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
