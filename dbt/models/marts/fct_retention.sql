-- Case 02 — N-day retention by signup-month cohort.
-- Question: what share of users from each signup-month cohort returned on
--   exactly day 1, 7, and 30 after signup?
-- Parity: identical logic to cases/02_n_day_retention.sql; pinned by the
--   golden test tests/assert_golden_retention.sql.
with flags as (
    select
        u.user_id,
        date_trunc('month', u.signup_date) as cohort,
        max(case when e.event_date = u.signup_date + 1 then 1 else 0 end) as d1,
        max(case when e.event_date = u.signup_date + 7 then 1 else 0 end) as d7,
        max(case when e.event_date = u.signup_date + 30 then 1 else 0 end) as d30
    from {{ ref('stg_users') }} u
    left join {{ ref('stg_events') }} e on e.user_id = u.user_id
    group by u.user_id, u.signup_date
)
select
    cohort,
    count(*) as users,
    round(avg(d1) * 100, 2) as d1_retention,
    round(avg(d7) * 100, 2) as d7_retention,
    round(avg(d30) * 100, 2) as d30_retention
from flags
group by cohort
order by cohort
