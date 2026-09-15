-- 25. Purchase -> subscription conversion & time-to-convert.
-- Question: Of purchasers, who converts to a paid subscription, and how fast?
-- Approach: subscribers / purchasers by plan; days from first order to
--   subscription start (median/p90). 30% of purchasers subscribe by design, so
--   the case should "find" that conversion rate and the timing distribution.

WITH first_orders AS (
    SELECT user_id, MIN(order_ts) AS first_order FROM orders GROUP BY user_id
),
converted AS (
    SELECT fo.user_id, fo.first_order, s.plan, s.started_at,
           DATEDIFF('day', fo.first_order, s.started_at) AS days_to_convert
    FROM first_orders fo
    JOIN subscriptions s USING (user_id)
)
SELECT m.metric, m.value
FROM (
    SELECT 'purchasers' AS metric,
           CAST((SELECT COUNT(*) FROM first_orders) AS VARCHAR) AS value
    UNION ALL
    SELECT 'subscribers',
           CAST((SELECT COUNT(*) FROM converted) AS VARCHAR)
    UNION ALL
    SELECT 'conversion_pct',
           CAST(ROUND(100.0 * (SELECT COUNT(*) FROM converted) / (SELECT COUNT(*) FROM first_orders), 1) AS VARCHAR)
    UNION ALL
    SELECT 'monthly_subs', CAST(COUNT(*) FILTER (WHERE plan = 'monthly') AS VARCHAR) FROM converted
    UNION ALL
    SELECT 'annual_subs', CAST(COUNT(*) FILTER (WHERE plan = 'annual') AS VARCHAR) FROM converted
    UNION ALL
    SELECT 'median_days_to_convert', CAST(ROUND(MEDIAN(days_to_convert), 0) AS VARCHAR) FROM converted
    UNION ALL
    SELECT 'p90_days_to_convert', CAST(ROUND(QUANTILE_CONT(days_to_convert, 0.9), 0) AS VARCHAR) FROM converted
) m;