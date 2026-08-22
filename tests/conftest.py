"""Pytest config: ensure the DuckDB fixture exists before running tests."""

import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).parent.parent
DB = ROOT / "data" / "analytics.duckdb"


def pytest_configure():
    if not DB.exists():
        subprocess.run(
            [sys.executable, str(ROOT / "data" / "generate_data.py")], check=True
        )
