-- Business-rule test: funnel sessions must strictly decrease at every step.
-- Any row returned means a downstream step has >= sessions of the previous one.
select
    a.event_name,
    a.sessions,
    b.sessions as next_sessions
from {{ ref('fct_funnel') }} a
join {{ ref('fct_funnel') }} b on b.pos = a.pos + 1
where b.sessions >= a.sessions
