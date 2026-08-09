-- 03. Rolling 30-day retention by cohort.
-- Question: Of users signed up in month M, what % were active at least once in
--   each 30-day window starting D days after signup (D = 7,14,30,60)?
-- Approach: EXISTS subquery per user for each window [signup+D, signup+D+30).
WITH active_days AS (
    SELECT user_id, DATE(event_time) AS d FROM events
),
windows AS (
    SELECT u.user_id,
           DATE_TRUNC('month', u.signup_date) AS cohort,
           EXISTS(SELECT 1 FROM active_days a WHERE a.user_id = u.user_id
                    AND a.d >= u.signup_date + 7  AND a.d < u.signup_date + 37)  AS w07,
           EXISTS(SELECT 1 FROM active_days a WHERE a.user_id = u.user_id
                    AND a.d >= u.signup_date + 14 AND a.d < u.signup_date + 44) AS w14,
           EXISTS(SELECT 1 FROM active_days a WHERE a.user_id = u.user_id
                    AND a.d >= u.signup_date + 30 AND a.d < u.signup_date + 60) AS w30,
           EXISTS(SELECT 1 FROM active_days a WHERE a.user_id = u.user_id
                    AND a.d >= u.signup_date + 60 AND a.d < u.signup_date + 90) AS w60
    FROM users u
)
SELECT cohort, COUNT(*) AS users,
       ROUND(AVG(CAST(w07 AS INT))*100,2) AS win_7d,
       ROUND(AVG(CAST(w14 AS INT))*100,2) AS win_14d,
       ROUND(AVG(CAST(w30 AS INT))*100,2) AS win_30d,
       ROUND(AVG(CAST(w60 AS INT))*100,2) AS win_60d
FROM windows
GROUP BY cohort
ORDER BY cohort;
