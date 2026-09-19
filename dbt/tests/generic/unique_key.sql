{% test unique_key(model, columns) %}
-- Generic test: assert the given column(s) form a unique key (no duplicates).
-- Mirrors dbt_utils.unique_combination_of_columns, without the dependency.
select
    {% for column_name in columns %}
    "{{ column_name }}"::text ||
    {% endfor %}
    ''
from {{ model }}
group by 1
having count(*) > 1
{% endtest %}
