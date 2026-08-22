-- 15. Order amount distribution by category (median, p90, p99).
-- Question: What is the spend distribution per product category, and where
--   are the expensive tail purchases (useful for AOV guards and fraud rules)?
-- Approach: MEDIAN() and QUANTILE_CONT(amount, k) window/aggregate functions;
--   compare central tendency (median) vs tail (p99) to spot fat-tailed
--   categories.
SELECT product_category,
       COUNT(*)                    AS orders,
       ROUND(MEDIAN(amount), 2)     AS median_amount,
       ROUND(QUANTILE_CONT(amount, 0.90), 2) AS p90,
       ROUND(QUANTILE_CONT(amount, 0.99), 2) AS p99,
       ROUND(SUM(amount), 2)        AS total_revenue
FROM orders
GROUP BY product_category
ORDER BY total_revenue DESC;