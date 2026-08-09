# SQL Analytics Case Study

A take-home–style SQL analytics portfolio: 10 end-to-end case studies on a
synthetic product dataset, runnable on DuckDB. Each case is one self-contained
`.sql` file with the question and approach as a leading comment.

No server, no credentials — one command builds the data and the database.

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
| 09 | A/B conversion by variant | left join, `LAG` for lift |
| 10 | Revenue attribution | first-touch vs lifetime, correlated subquery |

## Data

Synthetic, deterministic (seed = 42). One run produces identical output.

- **Users** — 20,000 signups over Jan–Jun 2024, with `channel`, `country`, `device`, `ab_variant`.
- **Events** — ~183k funnel events (`app_open → view_item → add_to_cart → checkout → purchase`) across 80k sessions.
- **Orders** — ~800 purchases with amount and product category.
- **Subscriptions** — ~240 conversions to monthly/annual plans.

Schema: [`data/schema.sql`](data/schema.sql). Generator: [`data/generate_data.py`](data/generate_data.py).

Engagement decays geometrically from signup; retention is weighted by acquisition
channel, so cohorts and channels produce visible, non-trivial differences.

## Quick start

```bash
# Python >=3.10. Dependencies: duckdb, pandas, numpy (pytest for tests).
uv run --with duckdb --with pandas --with numpy python data/generate_data.py   # build data/analytics.duckdb
uv run --with duckdb --with pandas python run.py            # list cases
uv run --with duckdb --with pandas python run.py 1          # run a case
uv run --with duckdb --with pandas python run.py 4 --limit 20
```

Tests (regression invariants per case):

```bash
uv run --with duckdb --with pandas --with numpy --with pytest pytest -q
```

The runner prints the case's question, executes the SQL against
`data/analytics.duckdb`, and renders the result as a table.

## Ad-hoc exploration

```bash
uv run --with duckdb python -c "import duckdb; print(duckdb.connect('data/analytics.duckdb', read_only=True).execute('SELECT channel, COUNT(*) FROM users GROUP BY channel').fetchall())"
```

## Layout

```
sql-analytics-case-study/
├── data/
│   ├── schema.sql            # CREATE TABLE definitions
│   ├── generate_data.py      # deterministic synthetic data + DuckDB build
│   └── analytics.duckdb      # generated (gitignored)
├── cases/                    # one .sql per case
├── tests/
│   ├── conftest.py           # auto-builds the DB if missing
│   └── test_expected_results.py
├── run.py                    # CLI runner
└── cases.md                  # all cases with answers + notes
```

## Notes

- DuckDB chosen for analytic SQL: window functions, range joins, `DATE` arithmetic, single-file DB, no server.
- Every case is pure SQL — no Python glue. `run.py` is just a convenience wrapper.
- The synthetic data is intentionally realistic enough that case answers reveal
  business signal (e.g. referral channel over-indexes on retention; funnel drops
  hardest at add-to-cart → checkout).
