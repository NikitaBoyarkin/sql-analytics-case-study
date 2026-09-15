-- 18. Cohort revenue retention (revenue triangle).
-- Question: How does revenue from each signup cohort evolve by months-since-
--   signup, and does revenue retention decay as fast as activity retention
--   (cases 02/03)?
-- Approach: cohort = signup month; period = months since signup. Per-period
--   (non-cumulative) revenue forms the triangle, indexed to % of period-0,
--   plus cumulative revenue and LTV per user for each period.

WITH cohorts AS (
    SELECT user_id, DATE_TRUNC('month', signup_date) AS cohort FROM users
),
rev AS (
    SELECT user_id, DATE_TRUNC('month', order_ts) AS m, SUM(amount) AS amt
    FROM orders GROUP BY user_id, DATE_TRUNC('month', order_ts)
),
joined AS (
    SELECT c.cohort, r.user_id, r.m, r.amt,
           (EXTRACT(YEAR FROM r.m) - EXTRACT(YEAR FROM c.cohort)) * 12
           + (EXTRACT(MONTH FROM r.m) - EXTRACT(MONTH FROM c.cohort)) AS period
    FROM cohorts c
    JOIN rev r USING (user_id)
),
triangle AS (
    SELECT cohort, period,
           COUNT(DISTINCT user_id) AS paying_users,
           ROUND(SUM(amt), 2) AS revenue
    FROM joined GROUP BY cohort, period
),
p0 AS (
    SELECT cohort, revenue AS p0_revenue FROM triangle WHERE period = 0
),
cum AS (
    SELECT cohort, period, revenue,
           ROUND(SUM(revenue) OVER (PARTITION BY cohort ORDER BY period
                                    ROWS UNBOUNDED PRECEDING), 2) AS cum_revenue
    FROM triangle
)
SELECT t.cohort,
       t.period,
       t.paying_users,
       t.revenue,
       ROUND(100.0 * t.revenue / p.p0_revenue, 1) AS pct_of_period0,
       c.cum_revenue,
       ROUND(c.cum_revenue / (SELECT COUNT(*) FROM users u
                              WHERE DATE_TRUNC('month', u.signup_date) = t.cohort), 2) AS ltv_per_user
FROM triangle t
JOIN p0 p USING (cohort)
JOIN cum c USING (cohort, period)
ORDER BY t.cohort, t.period;