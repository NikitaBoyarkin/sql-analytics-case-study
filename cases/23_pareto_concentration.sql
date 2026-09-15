-- 23. Pareto / revenue concentration.
-- Question: What share of revenue comes from the top deciles of buyers — and is
--   there a whale tier worth productizing for?
-- Approach: per-buyer lifetime revenue; NTILE(10) on revenue descending; report
--   each decile's buyer/revenue share plus the cumulative revenue curve.

WITH buyers AS (
    SELECT user_id, ROUND(SUM(amount), 2) AS revenue FROM orders GROUP BY user_id
),
deciles AS (
    SELECT user_id, revenue,
           NTILE(10) OVER (ORDER BY revenue DESC) AS decile
    FROM buyers
),
agg AS (
    SELECT decile,
           COUNT(*) AS buyers,
           ROUND(SUM(revenue), 2) AS revenue,
           ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM buyers), 2) AS pct_of_buyers,
           ROUND(100.0 * SUM(revenue) / (SELECT SUM(revenue) FROM buyers), 2) AS pct_of_revenue
    FROM deciles
    GROUP BY decile
)
SELECT decile,
       buyers,
       revenue,
       pct_of_buyers,
       pct_of_revenue,
       ROUND(SUM(pct_of_revenue) OVER (ORDER BY decile ROWS UNBOUNDED PRECEDING), 2) AS cum_pct
FROM agg
ORDER BY decile;