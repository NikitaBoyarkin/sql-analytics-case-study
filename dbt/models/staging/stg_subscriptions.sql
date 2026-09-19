-- Staging: subscription records, one row per subscription.
select
    sub_id,
    user_id,
    started_at,
    plan,
    amount
from {{ source('raw', 'subscriptions') }}
