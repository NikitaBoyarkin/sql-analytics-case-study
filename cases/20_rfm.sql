-- 20. RFM segmentation (NTILE quintiles).
-- Question: Which buyer segments deserve the most attention, and where does
--   revenue concentrate?
-- Approach: NTILE(5) on recency (days since last order, inverted so 5 = most
--   recent), frequency (order count), monetary (lifetime revenue). Simple score
--   rules -> segment labels. Report segment size and revenue share.

WITH last_order AS (
    SELECT MAX(order_ts) AS max_ts FROM orders
),
buyers AS (
    SELECT user_id,
           DATEDIFF('day', MAX(order_ts), (SELECT max_ts FROM last_order)) AS recency_days,
           COUNT(*) AS frequency,
           ROUND(SUM(amount), 2) AS monetary
    FROM orders GROUP BY user_id
),
scored AS (
    SELECT user_id, recency_days, frequency, monetary,
           NTILE(5) OVER (ORDER BY recency_days ASC) AS r,  -- 5 = most recent
           NTILE(5) OVER (ORDER BY frequency ASC)    AS f,  -- 5 = most orders
           NTILE(5) OVER (ORDER BY monetary ASC)     AS m   -- 5 = highest spend
    FROM buyers
),
segmented AS (
    SELECT *,
           CASE WHEN r = 5 AND f >= 4        THEN 'Champions'
                WHEN r >= 4 AND f >= 3       THEN 'Loyal'
                WHEN r <= 2 AND f >= 4       THEN 'Big Spenders'
                WHEN r <= 2 AND f >= 2       THEN 'At Risk'
                WHEN r <= 2                  THEN 'Hibernating'
                WHEN r >= 4 AND f <= 2       THEN 'Promising'
                ELSE 'Regular' END AS segment
    FROM scored
)
SELECT segment,
       COUNT(*) AS buyers,
       ROUND(SUM(monetary), 2) AS revenue,
       ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM buyers), 1) AS pct_of_buyers,
       ROUND(100.0 * SUM(monetary) / (SELECT SUM(monetary) FROM buyers), 1) AS pct_of_revenue
FROM segmented
GROUP BY segment
ORDER BY revenue DESC;