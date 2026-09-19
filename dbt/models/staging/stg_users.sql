-- Staging: users, lightly typed. One row per user.
select
    user_id,
    signup_date,
    channel,
    country,
    device,
    ab_variant
from {{ source('raw', 'users') }}
