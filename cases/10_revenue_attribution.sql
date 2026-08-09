-- 10. Attribution: lifetime vs first-touch revenue by acquisition channel.
-- Question: How much revenue is attributed to each signup channel under
--   all-time (lifetime) vs first-touch (first order only) models?
-- Approach: channel = users.channel (acquisition); lifetime = SUM(all orders);
--   first-touch = amount of each user's earliest order.
WITH user_rev AS (
    SELECT u.channel, u.user_id,
           SUM(o.amount) AS lifetime_rev,
           (SELECT o2.amount FROM orders o2
            WHERE o2.user_id = u.user_id
            ORDER BY o2.order_ts LIMIT 1) AS first_order_rev
    FROM users u
    LEFT JOIN orders o ON o.user_id = u.user_id
    GROUP BY u.channel, u.user_id
)
SELECT channel,
       ROUND(SUM(lifetime_rev), 2)    AS lifetime_revenue,
       ROUND(SUM(first_order_rev), 2) AS first_touch_revenue
FROM user_rev
GROUP BY channel
ORDER BY lifetime_revenue DESC;
