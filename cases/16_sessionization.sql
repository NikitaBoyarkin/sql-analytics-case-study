-- 16. Sessionization from raw timestamps + session-depth metrics.
-- Question: Can we reconstruct user sessions from raw event timestamps alone
--   (ignoring the pre-assigned session_id), and how deep is the typical session?
-- Approach: gaps-and-islands on event_time — a new session starts whenever the
--   gap from the previous event exceeds 30 minutes (industry standard). Derive
--   sessions, validate against the provided session_id (~99.6% fidelity: 298
--   same-day back-to-back sessions closer than 30 min get merged, none split),
--   then report the session-depth distribution and median duration.

WITH ordered AS (
    SELECT user_id, session_id, event_time,
           LAG(event_time) OVER (PARTITION BY user_id ORDER BY event_time) AS prev_t
    FROM events
),
flagged AS (
    SELECT user_id, session_id, event_time,
           CASE WHEN prev_t IS NULL
                  OR event_time - prev_t > INTERVAL 30 MINUTE
                THEN 1 ELSE 0 END AS is_new
    FROM ordered
),
derived AS (
    SELECT user_id, session_id, event_time,
           SUM(is_new) OVER (PARTITION BY user_id ORDER BY event_time
                             ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS dses
    FROM flagged
),
per_session AS (
    SELECT user_id, dses,
           COUNT(*) AS events,
           DATEDIFF('minute', MIN(event_time), MAX(event_time)) AS duration_min
    FROM derived
    GROUP BY user_id, dses
),
validation AS (
    SELECT COUNT(*) AS derived_sessions,
           (SELECT COUNT(DISTINCT session_id) FROM events) AS true_sessions,
           ROUND(100.0 * COUNT(*) / (SELECT COUNT(DISTINCT session_id) FROM events), 1) AS fidelity_pct
    FROM per_session
),
merged AS (
    SELECT COUNT(*) AS merged_pairs
    FROM (SELECT user_id, dses, COUNT(DISTINCT session_id) AS n_true
          FROM derived GROUP BY user_id, dses) t
    WHERE t.n_true > 1
)
SELECT m.metric, m.value
FROM (
    SELECT 'derived_sessions' AS metric, CAST(derived_sessions AS VARCHAR) AS value FROM validation
    UNION ALL SELECT 'true_sessions',     CAST(true_sessions     AS VARCHAR) FROM validation
    UNION ALL SELECT 'fidelity_pct',      CAST(fidelity_pct      AS VARCHAR) FROM validation
    UNION ALL SELECT 'merged_pairs',      CAST(merged_pairs      AS VARCHAR) FROM merged
    UNION ALL SELECT 'sessions_1_event',    CAST(COUNT(*) FILTER (WHERE events = 1)            AS VARCHAR) FROM per_session
    UNION ALL SELECT 'sessions_2_3_events', CAST(COUNT(*) FILTER (WHERE events BETWEEN 2 AND 3) AS VARCHAR) FROM per_session
    UNION ALL SELECT 'sessions_4_5_events', CAST(COUNT(*) FILTER (WHERE events BETWEEN 4 AND 5) AS VARCHAR) FROM per_session
    UNION ALL SELECT 'sessions_6plus_events', CAST(COUNT(*) FILTER (WHERE events >= 6)          AS VARCHAR) FROM per_session
    UNION ALL SELECT 'median_events_per_session', CAST(MEDIAN(events)       AS VARCHAR) FROM per_session
    UNION ALL SELECT 'median_duration_min',       CAST(MEDIAN(duration_min) AS VARCHAR) FROM per_session
) m;