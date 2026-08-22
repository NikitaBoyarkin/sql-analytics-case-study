-- 13. Monthly revenue by product category (PIVOT).
-- Question: How does revenue split across product categories month by month?
-- Approach: aggregate revenue per (month, category), then PIVOT so each
--   category becomes its own column. Categories with no sales show NULL.
PIVOT (
    SELECT DATE_TRUNC('month', order_ts)::DATE AS month,
           product_category,
           SUM(amount) AS revenue
    FROM orders
    GROUP BY month, product_category
)
ON product_category
USING SUM(revenue)
ORDER BY month;