-- 05. LTV by signup-month cohort.
-- Question: Average revenue per user (LTV) by signup cohort.
-- Approach: cohort = month(signup_date); lifetime order revenue per user;
--   average across users in cohort.
WITH user_rev AS (
    SELECT u.user_id,
           DATE_TRUNC('month', u.signup_date) AS cohort,
           COALESCE(SUM(o.amount), 0) AS total_rev
    FROM users u
    LEFT JOIN orders o ON o.user_id = u.user_id
    GROUP BY u.user_id, u.signup_date
)
SELECT cohort, COUNT(*) AS users,
       ROUND(SUM(total_rev), 2)  AS revenue,
       ROUND(AVG(total_rev), 2)  AS ltv_per_user
FROM user_rev
GROUP BY cohort
ORDER BY cohort;
