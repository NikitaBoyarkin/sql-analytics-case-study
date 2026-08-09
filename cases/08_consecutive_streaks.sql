-- 08. Gaps-and-islands: longest streak of consecutive active days per user.
-- Question: For each user, the longest run of consecutive active days.
-- Approach: distinct (user, active day); ROW_NUMBER() over user by day;
--   epoch_day - rn is constant within a consecutive run (island key);
--   group by user+island → run length; take max per user.
WITH active_days AS (
    SELECT DISTINCT user_id, DATE(event_time) AS d FROM events
),
ranked AS (
    SELECT user_id, d,
           ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY d) AS rn
    FROM active_days
),
islands AS (
    SELECT user_id,
           DATE_DIFF('day', DATE '2000-01-01', d) - rn AS island_key,
           COUNT(*) AS streak
    FROM ranked
    GROUP BY user_id, DATE_DIFF('day', DATE '2000-01-01', d) - rn
)
SELECT user_id, MAX(streak) AS longest_streak_days
FROM islands
GROUP BY user_id
ORDER BY longest_streak_days DESC, user_id
LIMIT 50;
