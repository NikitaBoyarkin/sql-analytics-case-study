"""Pin the claims the EDA figures make to the data they are drawn from.

The figures in `reports/eda/figures/` carry headline numbers in their titles and
callouts (fig1 is embedded in the README). An earlier revision hardcoded
"sharpest drop: cart->checkout = 77.8%" while the same chart drew -86% on the
next bar, and plotted a censored June retention cohort as a real 0% — both
survive a chart review and both are caught here instead.

Each assertion below restates a sentence a reader can see in a figure; if the
seed, the generator, or a metric definition moves, this fails and the figure
must be re-rendered (and the sentence re-worded) in the same change.

Run: uv run --extra dev pytest -q tests/test_figure_claims.py
"""

import importlib.util
import pathlib

import pandas as pd
import pytest

ROOT = pathlib.Path(__file__).parent.parent
FIG_DIR = ROOT / "reports" / "eda" / "figures"
SCRIPT = ROOT / "reports" / "eda" / "scripts" / "plot_figures.py"

FIGURES = [
    "fig1_funnel_steps.png",
    "fig2_order_amount_distribution.png",
    "fig3_conversion_by_channel.png",
    "fig4_weekly_order_revenue.png",
    "fig5_retention_decay.png",
    "fig6_retail_repeat_concentration.png",
]


def _figure_module():
    """Import the figure script by path (reports/eda/scripts is not a package)."""
    spec = importlib.util.spec_from_file_location("plot_figures", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def figmod():
    return _figure_module()


@pytest.fixture(scope="module")
def data(figmod):
    return figmod.load()


@pytest.fixture(scope="module")
def funnel(data, figmod):
    counts = (
        data["events"][data["events"]["event_name"].isin(figmod.FUNNEL)]
        .groupby("event_name")["session_id"]
        .nunique()
        .reindex(figmod.FUNNEL)
    )
    return pd.DataFrame(
        {
            "sessions": counts,
            "drop_pct": (100 - counts / counts.shift(1) * 100).round(2),
            "lost": counts.shift(1) - counts,
        }
    )


def test_fig1_payment_is_the_sharpest_drop(funnel):
    """fig1 title: 'payment is the sharpest cliff: 85.9% of checkouts never complete'."""
    assert funnel["drop_pct"].idxmax() == "purchase"
    assert funnel.loc["purchase", "drop_pct"] == pytest.approx(85.9, abs=0.15)


def test_fig1_cart_to_checkout_is_the_second_cliff(funnel):
    """fig1 callout + README: '77.8% of carts never reach checkout'."""
    assert funnel.loc["checkout", "drop_pct"] == pytest.approx(77.8, abs=0.15)
    assert funnel.loc["checkout", "drop_pct"] < funnel.loc["purchase", "drop_pct"] < 100


def test_fig1_largest_absolute_loss_is_view_to_cart(funnel):
    """fig1 callout: 'largest absolute loss: view item -> add to cart, 36,098 sessions'."""
    assert funnel["lost"].idxmax() == "add_to_cart"
    assert int(funnel.loc["add_to_cart", "lost"]) == 36_098


def test_fig5_june_cohort_is_censored(figmod, data):
    """fig5 must not plot a not-yet-observable day as a measured 0%."""
    table = figmod._retention_table(data["users"], data["events"])
    june = table.loc["2024-06"]
    assert pd.isna(june["d7"]) and pd.isna(june["d30"])
    assert june["cov30"] == 0.0
    assert june["cov7"] < 0.95  # partial window: also withheld, not averaged in
    assert not pd.isna(june["d1"])  # D1 is observable, so it stays


def test_fig5_title_means_come_from_mature_cohorts(figmod, data):
    """fig5 title: '19.6% (D1) -> 15.5% (D7) -> 5.0% (D30) on fully observed cohorts'."""
    table = figmod._retention_table(data["users"], data["events"])
    assert table["d1"].mean() == pytest.approx(19.6, abs=0.1)
    assert table["d7"].mean() == pytest.approx(15.5, abs=0.1)
    assert table["d30"].mean() == pytest.approx(5.0, abs=0.1)
    # the censored June zero must not be able to drag the D30 mean down
    assert table["d30"].min() > 4.0


def test_fig6_real_data_whale_bucket(figmod, data):
    """fig6 title: '14.9% of customers (11+ orders) carry 65% of revenue'."""
    con = figmod.duckdb.connect()
    try:
        df = con.execute(
            f"""
            WITH invoices AS (
                SELECT customer_id, invoice, SUM(quantity * price) AS rev
                FROM read_parquet('{ROOT / "data" / "realdata" / "online_retail.parquet"}')
                WHERE customer_id IS NOT NULL AND NOT is_cancellation
                  AND quantity > 0 AND price > 0
                GROUP BY customer_id, invoice
            ), cust AS (
                SELECT customer_id, COUNT(*) AS orders, SUM(rev) AS rev
                FROM invoices GROUP BY customer_id
            )
            SELECT ROUND(100.0 * COUNT(*) FILTER (WHERE orders >= 11) / COUNT(*), 2) AS cust_pct,
                   ROUND(100.0 * SUM(rev) FILTER (WHERE orders >= 11) / SUM(rev), 2) AS rev_pct
            FROM cust
            """
        ).df()
    finally:
        con.close()
    assert df["cust_pct"].iloc[0] == pytest.approx(14.9, abs=0.1)
    assert df["rev_pct"].iloc[0] == pytest.approx(65.0, abs=0.5)


def test_figures_exist_and_are_metadata_stable():
    """Every figure is present and carries no matplotlib version stamp.

    The version stamp is the only byte that changes between matplotlib releases,
    so stripping it keeps a re-render diffable instead of noisy.
    """
    for name in FIGURES:
        path = FIG_DIR / name
        assert path.is_file(), f"missing figure: {name}"
        assert path.stat().st_size > 20_000, f"suspiciously small figure: {name}"
        assert b"Software\x00Matplotlib" not in path.read_bytes()


@pytest.fixture
def rendered(figmod, monkeypatch):
    """Capture figures instead of writing them, so titles can be asserted on."""
    captured: dict[str, object] = {}

    def fake_save(fig, name):
        captured[name] = fig

    monkeypatch.setattr(figmod, "save", fake_save)
    return captured


@pytest.mark.parametrize(
    ("builder", "figure", "in_title", "in_body"),
    [
        # (which fig_* to call, which file it writes, title fragments, callout fragments)
        ("fig_funnel", "fig1_funnel_steps.png", ["85.9"], ["36,098"]),
        ("fig_retention", "fig5_retention_decay.png", ["19.6", "15.5", "5.0"], []),
    ],
)
def test_figure_text_is_derived_from_data(
    figmod, data, rendered, builder, figure, in_title, in_body
):
    """The headline in a title/callout must be the number the data yields.

    Guards the failure this suite was written for: a hardcoded "77.8% is the
    sharpest drop" sitting in a title while the same chart draws -86%. Change the
    data and the assertion moves; hardcode a number and it goes red.
    """
    import matplotlib.pyplot as plt

    if builder == "fig_funnel":
        figmod.fig_funnel(data["events"])
    else:
        figmod.fig_retention(data["users"], data["events"])

    fig = rendered[figure]
    try:
        title = " ".join(ax.get_title() for ax in fig.axes)
        body = " ".join(t.get_text() for ax in fig.axes for t in ax.texts)
    finally:
        plt.close(fig)

    for fragment in in_title:
        assert fragment in title, f"{figure} title: {fragment!r} missing from {title!r}"
    for fragment in in_body:
        assert fragment in body, f"{figure} callout: {fragment!r} missing from {body!r}"


def test_fig5_never_plots_the_censored_cohort(figmod, data, rendered):
    """No series may carry a value at the censored month — not even a pulled-down mean."""
    import matplotlib.pyplot as plt

    figmod.fig_retention(data["users"], data["events"])
    fig = rendered["fig5_retention_decay.png"]
    try:
        for line in fig.axes[0].get_lines():
            y = pd.Series(line.get_ydata(), dtype="float64")
            assert not (y.dropna() == 0).any(), "a censored cohort was drawn as 0%"
    finally:
        plt.close(fig)
