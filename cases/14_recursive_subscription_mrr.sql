-- 14. Subscription MRR via a recursive CTE.
-- Question: What is the monthly recurring revenue (MRR) from subscriptions,
--   and how does it grow over the observation window?
-- Approach: MRR convention — a monthly plan books its full amount each month;
--   an annual plan is recognized as amount/12 per month (ARR/12). A recursive
--   CTE expands each subscription into one row per billing month from
--   start through the end of June 2024; SUM per month gives MRR.
WITH RECURSIVE billings(month, user_id, plan, monthly_amount) AS (
    SELECT DATE_TRUNC('month', started_at)::DATE,
           user_id,
           plan,
           CASE WHEN plan = 'monthly' THEN amount ELSE amount / 12 END
    FROM subscriptions
    UNION ALL
    SELECT month + INTERVAL 1 MONTH, user_id, plan, monthly_amount
    FROM billings
    WHERE month < DATE '2024-06-01'
)
SELECT month,
       ROUND(SUM(monthly_amount), 2) AS mrr,
       COUNT(*)                      AS active_subs
FROM billings
GROUP BY month
ORDER BY month;