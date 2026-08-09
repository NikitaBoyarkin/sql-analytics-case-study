-- 02. N-day retention by signup cohort.
-- Question: What share of users from each signup-month cohort returned on
--   exactly day 1, 7, and 30 after signup?
-- Approach: cohort = month(signup_date); flag per user whether any event
--   happened on signup_date + N; average the flag per cohort.
WITH active_days AS (
    SELECT user_id, DATE(event_time) AS d FROM events
),
flags AS (
    SELECT u.user_id,
           DATE_TRUNC('month', u.signup_date) AS cohort,
           MAX(CASE WHEN a.d = u.signup_date + 1  THEN 1 ELSE 0 END) AS d1,
           MAX(CASE WHEN a.d = u.signup_date + 7  THEN 1 ELSE 0 END) AS d7,
           MAX(CASE WHEN a.d = u.signup_date + 30 THEN 1 ELSE 0 END) AS d30
    FROM users u
    LEFT JOIN active_days a ON a.user_id = u.user_id
    GROUP BY u.user_id, u.signup_date
)
SELECT cohort, COUNT(*) AS users,
       ROUND(AVG(d1)*100, 2)  AS d1_retention,
       ROUND(AVG(d7)*100, 2)  AS d7_retention,
       ROUND(AVG(d30)*100, 2) AS d30_retention
FROM flags
GROUP BY cohort
ORDER BY cohort;
