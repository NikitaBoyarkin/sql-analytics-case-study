#!/usr/bin/env bash
# Reproducible EDA for sql-analytics-case-study.
# Run from the project root:
#   bash reports/eda/scripts/run_profiles.sh
set -euo pipefail

EDA="/Users/nikitaboarkin/Desktop/00 ide/00 portfolio/.eda-tools/.venv/bin/python"
PROF="/Users/nikitaboarkin/Desktop/00 obsidian/obsidian/.claude/skills/eda/scripts/eda_profile.py"
OUT="reports/eda/scripts"

# Phase 1 — profiles on the two primaries + light profiles
"$EDA" "$PROF" --input data/orders.csv \
    --metric amount --segments product_category --time-col order_ts \
    --out "$OUT/profile_orders.md"

"$EDA" "$PROF" --input data/realdata/online_retail.parquet \
    --metric price --segments country,is_cancellation --time-col invoice_ts \
    --out "$OUT/profile_online_retail.md"

"$EDA" "$PROF" --input data/users.csv \
    --segments channel,country,device,ab_variant --time-col signup_date \
    --out "$OUT/profile_users.md"

"$EDA" "$PROF" --input data/events.csv \
    --segments event_name --time-col event_time \
    --out "$OUT/profile_events.md"

"$EDA" "$PROF" --input data/subscriptions.csv \
    --metric amount --segments plan --time-col started_at \
    --out "$OUT/profile_subscriptions.md"

# Phases 1-6 — truth checks, segment/funnel/retention/retail stats
"$EDA" reports/eda/scripts/eda_analysis.py

# Figures
"$EDA" reports/eda/scripts/plot_figures.py
