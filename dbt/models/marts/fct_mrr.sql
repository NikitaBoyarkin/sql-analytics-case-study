-- Case 14 — Subscription MRR via a recursive CTE.
-- Question: what is the monthly recurring revenue (MRR) from subscriptions, and
--   how does it grow over the observation window?
-- Convention: a monthly plan books its full amount each month; an annual plan is
--   recognized as amount / 12 (ARR/12). No proration. Recursive CTE expands each
--   subscription into one row per billing month through June 2024.
-- Parity: identical logic to cases/14_recursive_subscription_mrr.sql; pinned by
--   the golden test tests/assert_golden_mrr.sql.
with recursive billings(month, user_id, plan, monthly_amount) as (
    select
        cast(date_trunc('month', started_at) as date),
        user_id,
        plan,
        case when plan = 'monthly' then amount else amount / 12 end
    from {{ ref('stg_subscriptions') }}
    union all
    select
        month + interval 1 month,
        user_id,
        plan,
        monthly_amount
    from billings
    where month < date '2024-06-01'
)
select
    month,
    round(sum(monthly_amount), 2) as mrr,
    count(*) as active_subs
from billings
group by month
order by month
