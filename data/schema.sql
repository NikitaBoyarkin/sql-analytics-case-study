-- Analytics schema for the SQL case study.
-- Engine: DuckDB. Generated deterministically by generate_data.py (seed=42).

CREATE TABLE users (
    user_id      INTEGER PRIMARY KEY,
    signup_date  DATE,
    channel      VARCHAR,   -- organic | paid_search | social | referral | email
    country      VARCHAR,   -- RU | UA | KZ | BY | Other
    device       VARCHAR,   -- ios | android | web
    ab_variant   VARCHAR    -- control | treatment  (A/B assignment, see case 09)
);

CREATE TABLE events (
    event_id     INTEGER PRIMARY KEY,
    user_id      INTEGER REFERENCES users(user_id),
    session_id   INTEGER,
    event_time   TIMESTAMP,
    event_name   VARCHAR    -- app_open | view_item | add_to_cart | checkout | purchase
);

CREATE TABLE orders (
    order_id          INTEGER PRIMARY KEY,
    user_id           INTEGER REFERENCES users(user_id),
    order_ts          TIMESTAMP,
    amount            DOUBLE,
    product_category  VARCHAR    -- electronics | clothing | home | books | beauty | sports
);

CREATE TABLE subscriptions (
    sub_id      INTEGER PRIMARY KEY,
    user_id     INTEGER REFERENCES users(user_id),
    started_at  TIMESTAMP,
    plan        VARCHAR,   -- monthly | annual
    amount      DOUBLE
);
