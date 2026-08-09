"""CLI runner: execute a SQL case against data/analytics.duckdb and print results.

Usage:
    uv run python run.py            # list cases
    uv run python run.py 1          # run case 01_funnel_conversion.sql
    uv run python run.py 5 --limit 20
"""
from __future__ import annotations

import argparse
import pathlib
import sys

import duckdb

ROOT = pathlib.Path(__file__).parent
CASES = ROOT / "cases"
DB = ROOT / "data" / "analytics.duckdb"


def list_cases() -> list[pathlib.Path]:
    return sorted(CASES.glob("*.sql"))


def run_case(num: int, limit: int | None = None) -> None:
    matches = [p for p in list_cases() if int(p.name.split("_")[0]) == num]
    if not matches:
        print(f"No case #{num}. Available:", file=sys.stderr)
        for p in list_cases():
            print(f"  {p.name}", file=sys.stderr)
        sys.exit(1)
    path = matches[0]
    if not DB.exists():
        print("Database missing. Run: uv run python data/generate_data.py", file=sys.stderr)
        sys.exit(1)

    sql = path.read_text()
    print(f"\n=== {path.name} ===\n")
    # Heuristic: print the leading comment block (the question) before results.
    for line in sql.splitlines():
        if line.startswith("--"):
            print(line)
        else:
            break
    print()

    con = duckdb.connect(str(DB), read_only=True)
    try:
        df = con.execute(sql).fetchdf()
    finally:
        con.close()

    if limit:
        df = df.head(limit)
    with pd_option_context():
        print(df.to_string(index=False))
    print(f"\n[{len(df)} row{'s' if len(df) != 1 else ''}]")


def pd_option_context():
    import pandas as pd
    return pd.option_context("display.max_columns", None,
                             "display.width", 200,
                             "display.max_colwidth", 40)


def main() -> None:
    ap = argparse.ArgumentParser(description="Run a SQL analytics case study.")
    ap.add_argument("case", nargs="?", type=int, help="case number to run")
    ap.add_argument("--limit", type=int, default=None, help="max rows to print")
    args = ap.parse_args()

    if args.case is None:
        print("Available cases:")
        for p in list_cases():
            print(f"  {p.name.split('_')[0]:>2}  {p.stem}")
        print("\nRun: uv run python run.py <num>")
        return
    run_case(args.case, args.limit)


if __name__ == "__main__":
    main()
