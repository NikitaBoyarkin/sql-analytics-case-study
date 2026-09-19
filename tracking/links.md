# Tracking links

Short links to the live report, used to measure whether hiring managers actually
open it (audit risk #1). One row per link.

| Created | Short link | Destination | Channel | Notes |
|---------|-----------|-------------|---------|-------|
| _YYYY-MM-DD_ | _link_ | https://nikitaboyarkin.github.io/sql-analytics-case-study/ | _resume / DM / email_ | _e.g. Bitly or self-hosted redirect_ |

## Baseline: GitHub traffic (30 days)

Captured before outreach. Re-check weekly; append a row per check.

| Date checked | Views (30d) | Unique visitors | Top referrer | Notes |
|--------------|-------------|-----------------|--------------|-------|
| 2026-09-19 | 3 | 2 | github.com | pre-outreach baseline |

Raw source: `gh api repos/NikitaBoyarkin/sql-analytics-case-study/traffic/views`.

## How to create a link

- **Bitly:** shorten the Pages URL, enable click analytics, label by channel.
- **Fallback (no account):** a self-hosted redirect or a distinct UTM on the
  Pages URL; log the destination + created date here.
