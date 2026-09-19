-- Case 01 — Funnel: session-level conversion.
-- Question: for each funnel step, how many sessions reached it, and what is the
--   step-to-step and overall (vs app_open) conversion?
-- Parity: identical logic to cases/01_funnel_conversion.sql; pinned by the
--   golden test tests/assert_golden_funnel.sql.
with step_counts as (
    select event_name, count(distinct session_id) as sessions
    from {{ ref('stg_events') }}
    where event_name in ('app_open', 'view_item', 'add_to_cart', 'checkout', 'purchase')
    group by event_name
),
ordered as (
    select
        event_name,
        sessions,
        row_number() over (
            order by case event_name
                when 'app_open' then 1
                when 'view_item' then 2
                when 'add_to_cart' then 3
                when 'checkout' then 4
                when 'purchase' then 5
            end
        ) as pos
    from step_counts
)
select
    event_name,
    sessions,
    pos,
    round(sessions * 100.0 / first_value(sessions) over (order by pos), 2) as overall_pct,
    round(sessions * 100.0 / lag(sessions) over (order by pos), 2) as step_pct
from ordered
order by pos
