"""Build the real-data table for case 26 from the UCI Online Retail II dataset.

Source : UCI Machine Learning Repository, dataset id 502 "Online Retail II"
         https://archive.ics.uci.edu/dataset/502/online+retail+ii
License: CC BY 4.0 (redistribution with attribution is permitted)
Content: 1,067,371 invoice lines from a UK online retailer, 2009-12-01 → 2011-12-09.

This script downloads the source workbook (once, into data/realdata/raw/),
cleans it, and writes data/realdata/online_retail.parquet — a compact,
deterministic table that is committed to the repo so the case runs offline.

Run:
    uv run python data/realdata/build_realdata.py

Rebuilding is only needed to refresh the source; the committed parquet is what
the case and tests read.
"""

from __future__ import annotations

import pathlib
import urllib.request
import zipfile

import duckdb

HERE = pathlib.Path(__file__).parent
RAW_DIR = HERE / "raw"
ZIP_PATH = RAW_DIR / "online_retail_ii.zip"
XLSX_PATH = RAW_DIR / "online_retail_II.xlsx"
PARQUET = HERE / "online_retail.parquet"

URL = "https://archive.ics.uci.edu/static/public/502/online+retail+ii.zip"
SHEETS = ["Year 2009-2010", "Year 2010-2011"]

# Excel serial-date epoch offset, in days, from the Unix epoch (1970-01-01).
EXCEL_EPOCH_OFFSET = 25569


def download_source() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    if XLSX_PATH.exists():
        print(f"  source present: {XLSX_PATH.name}")
        return
    print(f"  downloading {URL}")
    urllib.request.urlretrieve(URL, ZIP_PATH)
    with zipfile.ZipFile(ZIP_PATH) as zf:
        zf.extract("online_retail_II.xlsx", RAW_DIR)


def sheet_sql(sheet: str) -> str:
    return (
        f"SELECT Invoice, StockCode, Description, Quantity, InvoiceDate, Price, "
        f'"Customer ID" AS customer_id, Country '
        f"FROM read_xlsx('{XLSX_PATH}', sheet='{sheet}', all_varchar=true)"
    )


def build() -> None:
    download_source()
    con = duckdb.connect()
    con.execute("INSTALL excel; LOAD excel;")
    con.execute("SET timezone='UTC'")
    union = " UNION ALL ".join(sheet_sql(s) for s in SHEETS)

    # InvoiceDate arrives as an Excel serial number; convert to a naive UTC
    # timestamp. TRY_CAST keeps malformed cells null instead of failing.
    con.execute(
        f"""
        CREATE TABLE online_retail AS
        SELECT
            Invoice                                   AS invoice,
            StockCode                                 AS stock_code,
            TRY_CAST(Quantity AS INTEGER)             AS quantity,
            (to_timestamp(
                (TRY_CAST(InvoiceDate AS DOUBLE) - {EXCEL_EPOCH_OFFSET}) * 86400
             ) AT TIME ZONE 'UTC')                    AS invoice_ts,
            TRY_CAST(Price AS DOUBLE)                 AS price,
            TRY_CAST(customer_id AS INTEGER)          AS customer_id,
            Country                                   AS country,
            (Invoice LIKE 'C%')                       AS is_cancellation
        FROM ({union})
        """
    )

    rows = con.execute("SELECT count(*) FROM online_retail").fetchone()[0]
    lo, hi = con.execute(
        "SELECT min(invoice_ts), max(invoice_ts) FROM online_retail"
    ).fetchone()
    con.execute(f"COPY online_retail TO '{PARQUET}' (FORMAT PARQUET, COMPRESSION zstd)")
    size_mb = PARQUET.stat().st_size / 1e6
    print(f"  rows: {rows:,}  range: {lo.date()} → {hi.date()}")
    print(f"  wrote {PARQUET.relative_to(HERE.parent.parent)} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    build()
