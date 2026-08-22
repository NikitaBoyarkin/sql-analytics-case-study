-- 11. Trend: 7-day moving average of DAU.
-- Question: What is the day-level DAU and its 7-day moving average, so the
--   underlying trend is visible above weekly noise?
-- Approach: count distinct users per calendar day; AVG() as a window function
--   over the trailing 7 rows (ROWS BETWEEN 6 PRECEDING AND CURRENT ROW).
WITH daily AS (
    SELECT DATE(event_time) AS d, COUNT(DISTINCT user_id) AS dau
    FROM events
    GROUP BY DATE(event_time)
)
SELECT d,
       dau,
       ROUND(AVG(dau) OVER (ORDER BY d ROWS BETWEEN 6 PRECEDING AND CURRENT ROW), 1) AS dau_ma7
FROM daily
ORDER BY d;