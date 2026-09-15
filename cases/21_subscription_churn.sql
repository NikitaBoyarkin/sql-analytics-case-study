-- 21. Subscription churn: logo & MRR churn.
-- Question: What is monthly logo and MRR churn, and how fast does the sub base leak?
-- Approach: active subs at month start = started before the month and not yet
--   cancelled; churned in month = cancelled during that month (and started
--   before it). Logo churn = churned / at-start; MRR churn = revenue of churned
--   subs / MRR at start. MRR uses the same convention as case 14 (annual = ARR/12).

WITH months AS (
    SELECT DATE_TRUNC('month', d) AS m
    FROM generate_series(DATE '2024-02-01', DATE '2024-06-01', INTERVAL 1 MONTH) t(d)
),
subs AS (
    SELECT s.sub_id, s.plan,
           DATE_TRUNC('month', s.started_at) AS start_m,
           DATE_TRUNC('month', c.cancelled_at) AS cancel_m,
           CASE WHEN s.plan = 'annual' THEN s.amount / 12.0 ELSE s.amount END AS mrr
    FROM subscriptions s
    LEFT JOIN subscription_cancellations c USING (sub_id)
)
SELECT m.m,
       COUNT(*) FILTER (WHERE s.start_m < m.m
                        AND (s.cancel_m IS NULL OR s.cancel_m >= m.m)) AS subs_at_start,
       COUNT(*) FILTER (WHERE s.cancel_m = m.m AND s.start_m < m.m) AS churned,
       ROUND(100.0 * COUNT(*) FILTER (WHERE s.cancel_m = m.m AND s.start_m < m.m)
             / NULLIF(COUNT(*) FILTER (WHERE s.start_m < m.m
                                       AND (s.cancel_m IS NULL OR s.cancel_m >= m.m)), 0), 2) AS logo_churn_pct,
       ROUND(SUM(s.mrr) FILTER (WHERE s.start_m < m.m
                                AND (s.cancel_m IS NULL OR s.cancel_m >= m.m)), 2) AS mrr_at_start,
       ROUND(SUM(s.mrr) FILTER (WHERE s.cancel_m = m.m AND s.start_m < m.m), 2) AS mrr_churned,
       ROUND(100.0 * SUM(s.mrr) FILTER (WHERE s.cancel_m = m.m AND s.start_m < m.m)
             / NULLIF(SUM(s.mrr) FILTER (WHERE s.start_m < m.m
                                         AND (s.cancel_m IS NULL OR s.cancel_m >= m.m)), 0), 2) AS mrr_churn_pct
FROM months m
CROSS JOIN subs s
GROUP BY m.m
ORDER BY m.m;