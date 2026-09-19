-- 26. Real data — repeat purchase & revenue concentration (UCI Online Retail II).
-- Question: On a real two-year retail dataset, what share of customers repeat, and how concentrated is revenue?
-- Approach: collapse invoice lines to one row per (customer, invoice), then per
--   customer; bucket customers by order count; compute each bucket's share of
--   customers and of revenue with window sums. Purchases only (cancellations,
--   non-positive quantities/prices and guest lines excluded).
-- Source: UCI ML Repository id 502, CC BY 4.0 — see data/realdata/README.md.
WITH invoices AS (
    SELECT customer_id,
           invoice,
           SUM(quantity * price) AS invoice_revenue
    FROM online_retail
    WHERE customer_id IS NOT NULL
      AND NOT is_cancellation
      AND quantity > 0
      AND price > 0
    GROUP BY customer_id, invoice
),
per_customer AS (
    SELECT customer_id,
           COUNT(*)             AS orders,
           SUM(invoice_revenue) AS revenue
    FROM invoices
    GROUP BY customer_id
),
bucketed AS (
    SELECT customer_id, orders, revenue,
           CASE WHEN orders = 1   THEN '1'
                WHEN orders = 2   THEN '2'
                WHEN orders <= 5  THEN '3-5'
                WHEN orders <= 10 THEN '6-10'
                ELSE '11+' END AS bucket
    FROM per_customer
)
SELECT bucket,
       COUNT(*) AS customers,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS customer_share_pct,
       ROUND(SUM(revenue), 0) AS revenue,
       ROUND(100.0 * SUM(revenue) / SUM(SUM(revenue)) OVER (), 2) AS revenue_share_pct
FROM bucketed
GROUP BY bucket
ORDER BY MIN(orders);
