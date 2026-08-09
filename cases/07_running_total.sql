-- 07. Cumulative revenue by day.
-- Question: Daily revenue and the cumulative running total over time.
-- Approach: SUM(amount) per day; windowed SUM() ORDER BY day, UNBOUNDED PRECEDING.
WITH daily AS (
    SELECT DATE(order_ts) AS d, SUM(amount) AS revenue
    FROM orders GROUP BY d
)
SELECT d,
       ROUND(revenue, 2) AS daily_revenue,
       ROUND(SUM(revenue) OVER (ORDER BY d ROWS UNBOUNDED PRECEDING), 2) AS cumulative
FROM daily
ORDER BY d;
