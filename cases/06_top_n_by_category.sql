-- 06. Top-3 product categories by revenue, per country.
-- Question: Which 3 categories bring the most revenue in each country?
-- Approach: join orders→users, sum revenue by (country, category), rank within
--   country by revenue desc, keep top 3.
SELECT country, product_category, ROUND(revenue, 2) AS revenue, rnk
FROM (
    SELECT u.country, o.product_category,
           SUM(o.amount) AS revenue,
           ROW_NUMBER() OVER (PARTITION BY u.country ORDER BY SUM(o.amount) DESC) AS rnk
    FROM orders o JOIN users u ON u.user_id = o.user_id
    GROUP BY u.country, o.product_category
)
WHERE rnk <= 3
ORDER BY country, rnk;
