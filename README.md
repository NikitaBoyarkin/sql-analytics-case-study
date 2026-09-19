# SQL Analytics Case Study

A take-home–style SQL analytics portfolio: 25 end-to-end case studies on a
synthetic product dataset, plus one **real-data** case (UCI Online Retail II) —
runnable on DuckDB. Each case is one self-contained `.sql` file with the
question and approach as a leading comment.

No server, no credentials — one command builds the data and the database, and
one command renders the whole thing into a **self-contained HTML report with
charts** (`reports/index.html`).

## Three findings

> 1. The funnel drops **54%** at add-to-cart → checkout — 54% of carts never proceed.
> 2. Retention falls off a cliff: D1 **~21%** → D30 **~5%** — the leak is the onboarding window.
> 3. Only **3.5%** of buyers ever repeat — a one-and-done purchase engine.

**Resume / LinkedIn one-liner**

```text
SQL Analytics Case Study — 25 cases on DuckDB (live report + repo)
Funnel drop 54% at cart→checkout · D1→D30 retention 21%→5% · repeat rate 3.5%
25 deterministic cases, golden-answer tests, CI, dbt model layer.
```

## How to evaluate this in 5 minutes

**What it is:** 25 synthetic SQL analytics cases + 1 real-data case (UCI Online
Retail II) on DuckDB — funnel, retention, LTV, attribution, gaps-and-islands,
and an A/B test with statistics written in pure SQL.

**Three signals this proves:**

- **SQL depth** — window functions, `QUALIFY`, `PIVOT`, recursive CTEs, and a
  two-proportion z-test with a p-value computed entirely in SQL (case 09).
- **Product framing** — every case ends in a business signal, not just a query:
  where the funnel drops, where retention leaks, which lever is untouched.
- **Discipline** — 25 deterministic cases (seed 42) with invariant and
  golden-answer tests; the numbers in `cases.md` are pinned to the database and
  CI stays green.

**Fastest path:**

1. Open the live report → <https://nikitaboyarkin.github.io/sql-analytics-case-study/>
2. Read cases **01** (funnel), **09** (A/B lift), **19** (repeat engine),
   **26** (the same pattern on real data — and why it flips).
3. Model layer (staging → marts, tests) → see `dbt/`.

## Topics covered

| # | Case | Technique |
|---|------|-----------|
| 01 | Funnel conversion | cumulative counts, `LAG` / `FIRST_VALUE` |
| 02 | N-day retention by cohort | cohort = `DATE_TRUNC('month', signup_date)` |
| 03 | Rolling 30-day retention | `EXISTS` subqueries per window |
| 04 | DAU / MAU / stickiness | trailing-28d range join |
| 05 | LTV by cohort | left join + `COALESCE` for zero-revenue users |
| 06 | Top-N categories per country | `ROW_NUMBER() OVER (PARTITION BY ...)` |
| 07 | Cumulative revenue | windowed `SUM() ... UNBOUNDED PRECEDING` |
| 08 | Longest active-day streak | gaps-and-islands (`row_number` → island key) |
| 09 | A/B conversion by variant | two-proportion z-test in pure SQL (z, p-value, verdict) |
| 10 | Revenue attribution | first-touch vs lifetime, correlated subquery |
| 11 | 7-day moving average of DAU | `AVG() OVER (... ROWS BETWEEN 6 PRECEDING ...)` |
| 12 | Top-2 revenue users per country | `QUALIFY` (modern DuckDB filter-after-window) |
| 13 | Monthly revenue by category | `PIVOT` long → wide |
| 14 | Subscription MRR | recursive CTE (billing rows per subscription) |
| 15 | Order amount distribution | `MEDIAN`, `QUANTILE_CONT` (p90/p99) |
| 16 | Sessionization + session depth | gaps-and-islands on timestamps, validation vs ground truth |
| 17 | Weekly lifecycle (new/returning/resurrecting/dormant) | state transitions, `LAG`/`LEAD` |
| 18 | Cohort revenue retention (triangle) | months-since-signup self-join, % of period-0 |
| 19 | Repeat purchase & time between orders | `LAG` within user, repeat-rate |
| 20 | RFM segmentation | `NTILE` quintiles, segment-score rules |
| 21 | Subscription churn (logo & MRR) | monthly churn, `FILTER` aggregates |
| 22 | Refunds & net revenue | left join, gross-vs-net by month |
| 23 | Pareto / revenue concentration | `NTILE(10)`, cumulative-share curve |
| 24 | Daily revenue anomaly detection | robust MAD z-score, rolling baseline |
| 25 | Purchase → subscription conversion | join to subscriptions, time-to-convert |
| 26 | **Real data** — repeat purchase & concentration (UCI Online Retail II) | invoice→customer rollup, order-count buckets, revenue shares |

## Data

Synthetic, deterministic (seed = 42). One run produces identical output.

- **Users** — 20,000 signups over Jan–Jun 2024, with `channel`, `country`, `device`, `ab_variant`.
- **Events** — ~183k funnel events (`app_open → view_item → add_to_cart → checkout → purchase`) across 80k sessions.
- **Orders** — ~930 purchases with amount and product category.
- **Subscriptions** — ~270 conversions to monthly/annual plans.
- **Additive (cases 21–25, seed 43):** `subscription_cancellations` (~98) and
  `refunds` (~53) — generated on a *separate* RNG stream so the seed-42 tables
  above stay byte-identical and their golden answers hold.

Schema: [`data/schema.sql`](data/schema.sql). Generator: [`data/generate_data.py`](data/generate_data.py).

Engagement decays geometrically from signup; retention is weighted by acquisition
channel, so cohorts and channels produce visible, non-trivial differences. Sessions
are right-truncated (not clamped) at the observation end, and the A/B assignment
carries an **embedded treatment effect** so case 09 detects a real, significant
signal — a deliberate "find the lift" exercise.

### Real data (case 26)

Case 26 runs on the **UCI Online Retail II** dataset — 1,067,371 real invoice
lines from a UK online retailer (2009-12 → 2011-12), CC BY 4.0, no synthetic
scaffolding. The cleaned table ships as a committed 4.5 MB parquet
([`data/realdata/`](data/realdata/README.md)), loaded into the same DuckDB by the
generator, so the case runs offline against the same database as the synthetic
cases. It re-runs the repeat-purchase / concentration pattern and finds the
*inverse* of the synthetic engine: 72.4% of customers repeat and the top 15%
drive 65% of revenue.

## Quick start

```bash
# Python >=3.10. Dependencies: duckdb, pandas, numpy, matplotlib (pytest for tests).
uv sync --extra dev                    # install everything once
uv run python data/generate_data.py    # build data/analytics.duckdb
uv run python run.py                   # list cases
uv run python run.py 1                 # run a case
uv run python run.py 9 --limit 20      # run with a row limit
uv run python scripts/report.py        # render reports/index.html (charts + all cases)
```

The real-data table is committed, so no download is needed. To rebuild it from
the source workbook (once, ~44 MB): `uv run python data/realdata/build_realdata.py`.

Tests (regression invariants per case + golden answers pinned to cases.md):

```bash
uv run --extra dev pytest -q
```

The runner prints the case's question, executes the SQL against
`data/analytics.duckdb`, and renders the result as a table. The report script
renders every case as a chart + table in one shareable HTML file.

## dbt model layer

The same DuckDB file also has a dbt project (`dbt/`) proving the model layer:
staging → marts, with tests. Three cases are ported to dbt with **identical
golden numbers** to the hand-written SQL — enforced by tests inside `dbt build`.

- **Ported cases:** 01 funnel (`fct_funnel`), 02 retention (`fct_retention`),
  14 MRR (`fct_mrr`).
- **Staging:** `stg_users`, `stg_events`, `stg_subscriptions` (views over the
  raw tables via `source()`).
- **Tests (17 in `dbt build`):** `not_null`, `unique`, `relationships`,
  `accepted_values`, plus custom golden-answer tests and a funnel-monotonicity
  rule test.
- Models materialize into a separate `dbt` schema — the raw `main` tables and
  the 25 SQL cases are untouched.

```bash
uv sync --extra dbt                   # add dbt-core + dbt-duckdb
uv run python data/generate_data.py   # build the database (once)
cd dbt && uv run dbt build --profiles-dir .
```

`profiles.yml` targets DuckDB with no credentials, so it is safe to commit.

## Portfolio highlights

- **A/B test with statistics in pure SQL** (`cases/09_ab_test_join.sql`) — computes
  a two-proportion z-test, p-value (normal-CDF via Abramowitz–Stegun), and a
  significance verdict without any statistical library.
- **Modern DuckDB idioms** — `QUALIFY` (12), `PIVOT` (13), recursive CTE (14).
- **Classic analytical patterns** — funnel, retention (point + rolling), DAU/MAU,
  LTV, top-N, running totals, gaps-and-islands, attribution, percentiles.
- **Data-quality instinct** — right-truncation instead of end-clamping, so the DAU
  trend has no artificial end-of-window spike.
- **Regression tests** — every case has invariant tests + golden-answer tests that
  keep `cases.md` and the codebase in sync.
- **Sessionization with validation** (`cases/16_sessionization.sql`) — derives
  sessions from raw timestamps with a 30-min inactivity gap and proves the
  derivation against the pre-assigned ids (99.6% fidelity).
- **An honest business finding** — cases 19–20 reveal a 3.5% repeat rate and an
  even revenue distribution: the dataset is a one-and-done purchase engine, and
  RFM degenerates to a recency story. Saying "the repeat lever is the gap" is
  the interview answer, not the chart.
- **Additive data without breaking goldens** — cases 21–25 (churn, refunds,
  Pareto, anomaly detection, upsell conversion) run on two new tables generated
  on a separate RNG stream; the seed-42 numbers in cases 1–20 never move.
- **Real data, same SQL (case 26)** — the repeat-purchase/concentration pattern
  re-run on 1M+ real invoice lines (UCI Online Retail II, CC BY 4.0) flips the
  synthetic conclusion: 72.4% repeat vs 3.5%, top 15% = 65% of revenue vs no
  whale tier. The pattern transfers; the business answer is data-dependent.

## Interview talking points

1. **Funnel:** the biggest drop is add-to-cart → checkout (54% of carts never
   proceed). That is where instrumentation and UX effort should go first.
2. **Retention:** D1 ~19–21% is stable, but collapses to ~5% by D30 — the leak is
   in the onboarding window, not long-term engagement.
3. **A/B:** treatment converts higher (4.9% vs 3.8%, +1.1pp) and the lift is
   significant (z = 4.8, p < 0.01). Always state the analysis unit: user-level
   conversion (~4–5%) differs from session-level (~1%, case 01).
4. **Monetization:** referral out-earns its user share (repeat purchases), while
   paid_search is one-and-done — a signal for channel strategy.
5. **Subscriptions:** MRR compounds ~15× Jan→Jun ($170 → $2,500) — the durable
   growth engine.
6. **Repeat purchase:** only 3.5% of buyers ever return (896 buyers, 31 repeat)
   — this is a one-and-done purchase engine. When asked "what would you work on
   next", the repeat lever is the honest answer.
7. **Real data (case 26):** the identical repeat/concentration query on UCI
   Online Retail II gives the opposite answer — 72.4% repeat, top 15% = 65% of
   revenue. The transferable asset is the pattern + the discipline, not the
   synthetic number.

## Trade-offs & design notes

- **DuckDB over a server DB:** single-file, zero-config, window functions and
  `QUALIFY`/`PIVOT`/recursive CTEs all work the same as in Postgres — an easy
  demo and interview environment. The SQL itself is portable.
- **Pure SQL cases:** no Python glue in the analysis. `run.py` and `report.py`
  are presentation only, which keeps every case self-contained and reviewable.
- **Fixed seed = reproducibility, not freshness:** deterministic data means the
  answers are stable and testable; the downside is it is not "real" data. The
  patterns generalize directly.
- **Recursive CTE for MRR uses a full-month convention** (no proration) and
  recognizes annual plans as ARR/12 — stated assumptions, easy to change.

## Ad-hoc exploration

```bash
uv run python -c "import duckdb; print(duckdb.connect('data/analytics.duckdb', read_only=True).execute('SELECT channel, COUNT(*) FROM users GROUP BY channel').fetchall())"
```

## Layout

```
sql-analytics-case-study/
├── data/
│   ├── schema.sql            # CREATE TABLE definitions
│   ├── generate_data.py      # deterministic synthetic data + DuckDB build
│   ├── realdata/             # UCI Online Retail II: parquet + build script (case 26)
│   ├── analytics.duckdb      # generated (gitignored)
├── cases/                    # one .sql per case (25 synthetic + 1 real)
├── dbt/                      # dbt project: staging → marts + tests (DuckDB)
│   ├── dbt_project.yml
│   ├── profiles.yml          # duckdb target, no credentials
│   ├── models/staging/       # stg_users, stg_events, stg_subscriptions
│   ├── models/marts/         # fct_funnel, fct_retention, fct_mrr
│   └── tests/                # golden-answer + business-rule singular tests
├── log/                      # application log + interview-rate lift (REQ-008)
├── tracking/                 # tracking links + GitHub traffic baseline
├── scripts/
│   └── report.py             # HTML report generator with charts
├── tests/
│   ├── conftest.py           # auto-builds the DB if missing
│   ├── test_expected_results.py   # per-case regression invariants
│   └── test_golden_answers.py     # pins cases.md numbers to the DB
├── .github/workflows/ci.yml  # pytest + dbt build + report render on push/PR
├── run.py                    # CLI runner
└── cases.md                  # all cases with answers + notes
```

## Notes

- Every case is pure SQL. `run.py` and `report.py` are convenience wrappers.
- The synthetic data is intentionally realistic enough that case answers reveal
  business signal (e.g. referral channel over-indexes on retention; funnel drops
  hardest at add-to-cart → checkout).
- `cases.md` and `tests/test_golden_answers.py` are the two sources of truth for
  expected numbers — if one changes, the other must too.