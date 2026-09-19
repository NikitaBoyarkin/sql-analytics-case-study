# Data Dictionary — SQL Analytics Case Study

Canonical schema and metric definitions for the synthetic warehouse in
`data/analytics.duckdb` (built deterministically by `data/generate_data.py`,
seed 42). Numbers quoted in `cases.md` are pinned by `tests/test_golden_answers.py`
and the dbt golden tests.

## Tables overview

| Table | Grain | Rows (seed 42) | Description |
|---|---|---|---|
| `users` | one row per user | 20,000 | Signups with acquisition attributes and A/B assignment |
| `events` | one row per funnel event | ~86k | Session-level funnel steps |
| `orders` | one row per order | purchases | Orders derived from `purchase` events |
| `subscriptions` | one row per subscription | converted buyers | Monthly / annual plans |
| `subscription_cancellations` | one row per cancelled sub | seed 43 | Additive table for churn cases (21-25) |
| `refunds` | one row per refund | seed 43 | Additive table for refund cases (21-25) |
| `online_retail` | one row per invoice line | real data | UCI Online Retail II (case 26, not synthetic) |

## Columns

### users

| Column | Type | Description | Example |
|---|---|---|---|
| `user_id` | INTEGER | Primary key | `1` |
| `signup_date` | DATE | Signup day within 2024-01-01 .. 2024-06-30 | `2024-02-14` |
| `channel` | VARCHAR | Acquisition channel | `organic`, `paid_search`, `social`, `referral`, `email` |
| `country` | VARCHAR | Country | `RU`, `UA`, `KZ`, `BY`, `Other` |
| `device` | VARCHAR | Device | `ios`, `android`, `web` |
| `ab_variant` | VARCHAR | A/B assignment, 50/50, independent of attributes | `control`, `treatment` |

### events

| Column | Type | Description | Example |
|---|---|---|---|
| `event_id` | INTEGER | Primary key | `1` |
| `user_id` | INTEGER | FK to `users` | `1` |
| `session_id` | INTEGER | Session identifier | `42` |
| `event_time` | TIMESTAMP | Event instant | `2024-02-14 10:05:00` |
| `event_name` | VARCHAR | Funnel step, in order | `app_open`, `view_item`, `add_to_cart`, `checkout`, `purchase` |

### orders

| Column | Type | Description | Example |
|---|---|---|---|
| `order_id` | INTEGER | Primary key | `1` |
| `user_id` | INTEGER | FK to `users` | `1` |
| `order_ts` | TIMESTAMP | Order instant (= purchase event) | `2024-03-01 18:22:00` |
| `amount` | DOUBLE | Order value, log-normal (~$25 mean) | `31.40` |
| `product_category` | VARCHAR | Category | `electronics`, `clothing`, `home`, `books`, `beauty`, `sports` |

### subscriptions

| Column | Type | Description | Example |
|---|---|---|---|
| `sub_id` | INTEGER | Primary key | `1` |
| `user_id` | INTEGER | FK to `users` | `1` |
| `started_at` | TIMESTAMP | Subscription start | `2024-03-02 09:00:00` |
| `plan` | VARCHAR | Plan | `monthly`, `annual` |
| `amount` | DOUBLE | Plan price | `12.99` |

## Key metrics definitions

| Metric | Formula | Notes |
|---|---|---|
| Funnel step conversion | `sessions_at_step / sessions_prev_step` | Distinct `session_id` per `event_name`; overall = vs `app_open` |
| D-N retention | `users_active_on(signup + N) / cohort_users` | Cohort = `date_trunc('month', signup_date)`; N in {1, 7, 30} |
| MRR | `sum(monthly_amount)` per billing month | Monthly plan books full amount; annual plan = `amount / 12` (ARR/12), no proration |
| AOV | `avg(orders.amount)` | Per order |
| ARPU | `total_revenue / active_users` | Window-dependent; always name the window |
| Refund rate | `refund_orders / paid_orders` | Additive tables (seed 43) |

## Data quality rules

- `event_id`, `user_id`, `order_id`, `sub_id` are unique and non-null.
- Every `events.user_id`, `orders.user_id`, `subscriptions.user_id` exists in `users`.
- `event_name` is one of the five funnel steps.
- `amount` is strictly positive; `signup_date <= order_ts` where both apply.
- Funnel is monotonic: `sessions(step_i+1) <= sessions(step_i)`.

## Marts (dbt)

| Mart | Grain | Source case |
|---|---|---|
| `fct_funnel` | one row per funnel step | Case 01 |
| `fct_retention` | one row per signup-month cohort | Case 02 |
| `fct_mrr` | one row per billing month | Case 14 |

## Coverage

Synthetic window 2024-01-01 .. 2024-06-30; `online_retail` is real data (UCI Online
Retail II, CC BY 4.0, see `data/realdata/README.md`). All synthetic numbers are
reproducible from `SEED = 42` (and `SEED_ADDITIVE = 43` for the additive tables).
