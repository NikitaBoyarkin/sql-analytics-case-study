-- 22. Refunds & net revenue.
-- Question: How much gross revenue is refunded, and what is net revenue by month?
-- Approach: left join refunds to orders (an order can be refunded once, full or
--   half). Monthly gross, refunded, net and refund rate; then the same by
--   product category to see where refunds concentrate.

WITH rev AS (
    SELECT o.order_ts, o.product_category, o.amount,
           COALESCE(r.amount, 0) AS refunded
    FROM orders o
    LEFT JOIN refunds r USING (order_id)
)
SELECT DATE_TRUNC('month', order_ts) AS m,
       ROUND(SUM(amount), 2) AS gross,
       ROUND(SUM(refunded), 2) AS refunded,
       ROUND(SUM(amount) - SUM(refunded), 2) AS net,
       ROUND(100.0 * SUM(refunded) / SUM(amount), 2) AS refund_rate_pct
FROM rev
GROUP BY 1
ORDER BY 1;