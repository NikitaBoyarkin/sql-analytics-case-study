-- 24. Daily revenue anomaly detection.
-- Question: Which days deviate significantly from their own recent baseline?
-- Approach: daily revenue; trailing-14-day baseline median and MAD (robust to
--   the fat-tailed revenue distribution), modified z-score = 0.6745*(x-med)/MAD,
--   flagged at |z| >= 3. Baseline uses only prior days (no lookahead) and needs
--   >= 7 days of history.

WITH daily AS (
    SELECT DATE_TRUNC('day', order_ts) AS d, SUM(amount) AS revenue
    FROM orders GROUP BY 1
),
med AS (
    SELECT d, revenue,
           MEDIAN(revenue) OVER (ORDER BY d ROWS BETWEEN 14 PRECEDING AND 1 PRECEDING) AS base_median,
           COUNT(revenue) OVER (ORDER BY d ROWS BETWEEN 14 PRECEDING AND 1 PRECEDING) AS n_hist
    FROM daily
),
mad AS (
    SELECT d, revenue, base_median, n_hist,
           MEDIAN(ABS(revenue - base_median)) OVER (ORDER BY d ROWS BETWEEN 14 PRECEDING AND 1 PRECEDING) AS mad
    FROM med
)
SELECT d,
       ROUND(revenue, 2) AS daily_revenue,
       ROUND(base_median, 2) AS baseline_median,
       ROUND(0.6745 * (revenue - base_median) / NULLIF(mad, 0), 2) AS z_mad,
       CASE WHEN n_hist >= 7
                 AND ABS(0.6745 * (revenue - base_median) / NULLIF(mad, 0)) >= 3
            THEN 'YES' ELSE '' END AS anomalous
FROM mad
WHERE n_hist >= 7
ORDER BY d;