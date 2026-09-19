"""Interview-rate lift: portfolio link vs no link (PRD REQ-008).

Reads log/applications.csv and prints, per arm, the number of applications,
the interview rate, and the difference. An "interview" is any outcome in
{screen, interview, offer}. Rows with an empty outcome are still pending and
are excluded from the rates.

Usage:
    uv run python log/lift.py
"""

from __future__ import annotations

import csv
from pathlib import Path

LOG_PATH = Path(__file__).parent / "applications.csv"
INTERVIEW_OUTCOMES = {"screen", "interview", "offer"}
TRUE_VALUES = {"true", "1", "yes", "y"}


def _as_bool(value: str) -> bool:
    return value.strip().lower() in TRUE_VALUES


def load_rows(path: Path = LOG_PATH) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as fh:
        return [row for row in csv.DictReader(fh) if row.get("date")]


def interview_rate(
    rows: list[dict[str, str]], link_used: bool
) -> tuple[int, float | None]:
    """Return (resolved applications, interview rate) for one arm."""
    resolved = [
        r
        for r in rows
        if _as_bool(r.get("link_used", "")) is link_used
        and r.get("outcome", "").strip()
    ]
    if not resolved:
        return 0, None
    hits = sum(
        1 for r in resolved if r["outcome"].strip().lower() in INTERVIEW_OUTCOMES
    )
    return len(resolved), hits / len(resolved)


def main() -> None:
    rows = load_rows()
    print(f"application log: {LOG_PATH}  ({len(rows)} rows)\n")
    if not rows:
        print("No applications logged yet — see log/README.md for the protocol.")
        return

    n_with, rate_with = interview_rate(rows, True)
    n_without, rate_without = interview_rate(rows, False)

    def fmt(n: int, rate: float | None) -> str:
        return f"n={n:<4} interview rate={'—' if rate is None else f'{rate:.1%}'}"

    print(f"  link used     : {fmt(n_with, rate_with)}")
    print(f"  no link       : {fmt(n_without, rate_without)}")

    if rate_with is None or rate_without is None or rate_without == 0:
        print("\nLift: not enough resolved data in both arms yet.")
        return

    lift_pp = (rate_with - rate_without) * 100
    lift_rel = (rate_with - rate_without) / rate_without
    verdict = "keep the link" if lift_rel >= 0 else "change delivery, not the cases"
    print(f"\nLift: {lift_pp:+.1f}pp ({lift_rel:+.0%} relative) → {verdict}")


if __name__ == "__main__":
    main()
