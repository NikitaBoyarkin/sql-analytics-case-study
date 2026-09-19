-- Staging: funnel events, one row per event. Adds an event_date for retention.
select
    event_id,
    user_id,
    session_id,
    event_time,
    cast(event_time as date) as event_date,
    event_name
from {{ source('raw', 'events') }}
