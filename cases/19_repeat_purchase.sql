-- 19. Repeat purchase: frequency and time between orders.
-- Question: How repeatable is purchase behavior, and how quickly do repeat
--   buyers come back?
-- Approach: repeat rate = share of buyers with >=2 orders. Days between
--   consecutive orders via LAG within user (median/p90 among repeat buyers).
--   Orders-per-buyer distribution completes the picture.

WITH buyer_stats AS (
    SELECT user_id,
           COUNT(*) AS orders,
           DATEDIFF('day', MIN(order_ts), MAX(order_ts)) AS span_days
    FROM orders GROUP BY user_id
),
gaps AS (
    SELECT user_id, order_ts,
           DATEDIFF('day', LAG(order_ts) OVER (PARTITION BY user_id ORDER BY order_ts),
                    order_ts) AS days_between
    FROM orders
),
repeat_gaps AS (
    SELECT days_between FROM gaps WHERE days_between IS NOT NULL
),
summary AS (
    SELECT (SELECT COUNT(*) FROM buyer_stats) AS buyers,
           (SELECT COUNT(*) FROM buyer_stats WHERE orders >= 2) AS repeat_buyers,
           ROUND(100.0 * (SELECT COUNT(*) FROM buyer_stats WHERE orders >= 2)
                 / (SELECT COUNT(*) FROM buyer_stats), 1) AS repeat_rate_pct,
           ROUND(MEDIAN(days_between), 0) AS median_days_between,
           ROUND(QUANTILE_CONT(days_between, 0.9), 0) AS p90_days_between
    FROM repeat_gaps
)
SELECT m.metric, m.value
FROM (
    SELECT 'buyers' AS metric, CAST(buyers AS VARCHAR) AS value FROM summary
    UNION ALL SELECT 'repeat_buyers', CAST(repeat_buyers AS VARCHAR) FROM summary
    UNION ALL SELECT 'repeat_rate_pct', CAST(repeat_rate_pct AS VARCHAR) FROM summary
    UNION ALL SELECT 'median_days_between', CAST(median_days_between AS VARCHAR) FROM summary
    UNION ALL SELECT 'p90_days_between', CAST(p90_days_between AS VARCHAR) FROM summary
    UNION ALL SELECT 'buyers_1_order', CAST((SELECT COUNT(*) FROM buyer_stats WHERE orders = 1) AS VARCHAR) FROM summary
    UNION ALL SELECT 'buyers_2_orders', CAST((SELECT COUNT(*) FROM buyer_stats WHERE orders = 2) AS VARCHAR) FROM summary
    UNION ALL SELECT 'buyers_3_orders', CAST((SELECT COUNT(*) FROM buyer_stats WHERE orders = 3) AS VARCHAR) FROM summary
    UNION ALL SELECT 'buyers_4plus_orders', CAST((SELECT COUNT(*) FROM buyer_stats WHERE orders >= 4) AS VARCHAR) FROM summary
) m;