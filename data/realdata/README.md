# Real data — UCI Online Retail II

Case 26 runs on a **real** public dataset, proving the SQL patterns generalize
beyond the synthetic engine.

## Source & license

- **Dataset:** Online Retail II (UCI ML Repository, id 502)
- **URL:** <https://archive.ics.uci.edu/dataset/502/online+retail+ii>
- **License:** CC BY 4.0 — redistribution with attribution is permitted
- **Content:** 1,067,371 invoice lines from a UK-based online retailer,
  2009-12-01 → 2011-12-09. Two worksheets (`2009-2010`, `2010-2011`).

## Files

| File | Committed | Purpose |
|------|-----------|---------|
| `online_retail.parquet` | yes (≈4.5 MB, zstd) | Cleaned table read by case 26 + tests |
| `build_realdata.py` | yes | Downloads source, cleans, rebuilds the parquet |
| `raw/` | no (gitignored) | Downloaded workbook (≈44 MB), cache only |

## Schema (`online_retail`)

| Column | Type | Notes |
|--------|------|-------|
| `invoice` | VARCHAR | Invoice number; `C…` prefix = cancellation |
| `stock_code` | VARCHAR | Product / SKU |
| `quantity` | INTEGER | Units; negative on cancellations |
| `invoice_ts` | TIMESTAMP | Naive UTC (converted from Excel serial date) |
| `price` | DOUBLE | Unit price |
| `customer_id` | INTEGER | Nullable — 243,007 lines are guest/unattributed |
| `country` | VARCHAR | Customer country |
| `is_cancellation` | BOOLEAN | `invoice` starts with `C` |

The `Description` column is dropped to keep the committed file small; it is not
used by any case.

## Rebuild

The committed parquet is what the case reads — no network needed. To refresh:

```bash
uv run python data/realdata/build_realdata.py
```

This regenerates `online_retail.parquet` deterministically from the source
workbook. `data/generate_data.py` loads the parquet into `analytics.duckdb` as
the `online_retail` table, so case 26 runs against the same database as the
synthetic cases.
