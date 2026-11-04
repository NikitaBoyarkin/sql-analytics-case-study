-- 20. RFM segmentation (quintile recency + spend, value-based frequency).
-- Question: Which buyer segments deserve the most attention, and where does
--   revenue concentrate?
-- Approach: NTILE(5) quintiles on recency (5 = most recent) and on lifetime
--   spend (5 = highest); both window ORDER BYs carry a total tie-break, so the
--   bucket assignment cannot depend on physical row order or thread count.
--   Frequency is scored by value, not quintiles: 865 of 896 buyers ordered
--   exactly once, so a quintile edge would fall inside one huge tie block and
--   a fifth of the base would land in a bucket by tie-break alone. Labels read
--   the recency x spend grid; the repeat-buyer count travels alongside so the
--   frequency axis stays visible without pretending it discriminates.

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
           -- DESC puts the smallest recency in the last bucket: 5 = most recent
           NTILE(5) OVER (ORDER BY recency_days DESC, user_id) AS r,
           -- ASC puts the largest spend in the last bucket: 5 = highest spend
           NTILE(5) OVER (ORDER BY monetary ASC, user_id)      AS m,
           CASE WHEN frequency >= 3 THEN 5
                WHEN frequency = 2 THEN 4
                ELSE 1 END AS f
    FROM buyers
),
segmented AS (
    SELECT *,
           CASE WHEN r >= 4 AND m >= 4 THEN 'Champions'      -- recent, high spend
                WHEN r >= 4 AND m = 3  THEN 'Loyal'          -- recent, mid spend
                WHEN r >= 4            THEN 'Promising'      -- recent, low spend
                WHEN m >= 4            THEN 'Big Spenders'   -- high spend, lapsing
                WHEN r = 3 AND m = 3   THEN 'Regular'
                WHEN m = 3             THEN 'At Risk'        -- mid spend, stale
                ELSE 'Hibernating'                           -- low spend, stale
           END AS segment
    FROM scored
)
SELECT segment,
       COUNT(*) AS buyers,
       COUNT(*) FILTER (WHERE f >= 4) AS repeat_buyers,
       ROUND(SUM(monetary), 2) AS revenue,
       ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM buyers), 1) AS pct_of_buyers,
       ROUND(100.0 * SUM(monetary) / (SELECT SUM(monetary) FROM buyers), 1) AS pct_of_revenue
FROM segmented
GROUP BY segment
ORDER BY revenue DESC;
