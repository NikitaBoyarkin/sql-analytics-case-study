"""Deterministic synthetic data generator for the SQL analytics case study.

Builds 4 fact tables (users, events, orders, subscriptions) over ~6 months,
writes CSVs + a DuckDB file (data/analytics.duckdb) per data/schema.sql.

Reproducible: seed=42. Run:
    uv run python data/generate_data.py
"""

from __future__ import annotations

import pathlib

import duckdb
import numpy as np
import pandas as pd

HERE = pathlib.Path(__file__).parent
SCHEMA = (HERE / "schema.sql").read_text()
REALDATA = HERE / "realdata" / "online_retail.parquet"

SEED = 42
# Separate stream for additive tables (cases 21-25): must never draw from the
# seed-42 generator, or every golden answer shifts downstream.
SEED_ADDITIVE = 43
N_USERS = 20_000
N_SESSIONS = 80_000
START = pd.Timestamp("2024-01-01")
END = pd.Timestamp("2024-06-30")
DAYS = (END - START).days + 1

CHANNELS = ["organic", "paid_search", "social", "referral", "email"]
CHANNEL_PROB = [0.30, 0.25, 0.20, 0.15, 0.10]
# higher = better long-term retention (used to weight session assignment)
CHANNEL_RETAIN = {
    "organic": 0.90,
    "paid_search": 0.60,
    "social": 0.70,
    "referral": 0.95,
    "email": 0.80,
}
COUNTRIES = ["RU", "UA", "KZ", "BY", "Other"]
COUNTRY_PROB = [0.55, 0.12, 0.12, 0.08, 0.13]
DEVICES = ["ios", "android", "web"]
DEVICE_PROB = [0.40, 0.40, 0.20]

# Funnel conditional probabilities (step i only if step i-1 happened)
P_VIEW, P_CART, P_CHECKOUT, P_PURCHASE = 0.82, 0.45, 0.22, 0.13
# Embedded A/B effect (see case 09): treatment variant is 1.25x more likely
# to complete checkout -> purchase. Control stays at P_PURCHASE.
A_B_PURCHASE_LIFT = 1.25

PRODUCT_CATEGORIES = ["electronics", "clothing", "home", "books", "beauty", "sports"]


def build_users(rng: np.random.Generator) -> pd.DataFrame:
    uids = np.arange(1, N_USERS + 1)
    signup = START + pd.to_timedelta(rng.integers(0, DAYS, N_USERS), unit="D")
    channel = rng.choice(CHANNELS, N_USERS, p=CHANNEL_PROB)
    country = rng.choice(COUNTRIES, N_USERS, p=COUNTRY_PROB)
    device = rng.choice(DEVICES, N_USERS, p=DEVICE_PROB)
    # A/B assignment 50/50, independent of user attributes. The variant itself
    # carries an embedded treatment effect (see A_B_PURCHASE_LIFT), so case 09
    # can detect a real, interpretable signal.
    ab = np.where(rng.random(N_USERS) < 0.5, "control", "treatment")
    return pd.DataFrame(
        {
            "user_id": uids,
            "signup_date": signup.normalize().date,
            "channel": channel,
            "country": country,
            "device": device,
            "ab_variant": ab,
        }
    )


def build_events(
    rng: np.random.Generator, users: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Return (events, orders, subscriptions)."""
    weights = np.array([CHANNEL_RETAIN[c] for c in users["channel"]], dtype=float)
    weights /= weights.sum()
    uids = users["user_id"].values
    su = pd.to_datetime(users.set_index("user_id")["signup_date"])

    # Session dates follow a geometric decay from signup, but a session that
    # would fall after the observation window is NOT observed (right truncation).
    # Rejection-sample until we have exactly N_SESSIONS in-window sessions, so
    # no artificial pile-up is clamped onto the last calendar day.
    sess_user: list[int] = []
    sess_offsets: list[int] = []
    while len(sess_user) < N_SESSIONS:
        batch = max(N_SESSIONS - len(sess_user), 1000)
        cand = rng.choice(uids, batch, p=weights)
        cand_su = su.loc[cand].values
        cand_off = rng.geometric(0.05, batch).tolist()
        in_window = (cand_su + pd.to_timedelta(cand_off, unit="D")) <= END
        sess_user.extend(cand[in_window].tolist())
        sess_offsets.extend(np.array(cand_off)[in_window].tolist())
    sess_user = np.array(sess_user[:N_SESSIONS], dtype=np.int64)
    sess_offsets = np.array(sess_offsets[:N_SESSIONS])

    su_ts = su.loc[sess_user].values
    sess_date = su_ts + pd.to_timedelta(sess_offsets, unit="D")
    hour = rng.integers(6, 24, N_SESSIONS)
    minute = rng.integers(0, 60, N_SESSIONS)
    sess_ts = sess_date + pd.to_timedelta(hour * 60 + minute, unit="m")

    session_id = np.arange(1, N_SESSIONS + 1)

    # Funnel masks (each conditional on previous step).
    view = rng.random(N_SESSIONS) < P_VIEW
    cart = view & (rng.random(N_SESSIONS) < P_CART)
    checkout = cart & (rng.random(N_SESSIONS) < P_CHECKOUT)
    # A/B effect: treatment sessions convert checkout->purchase at a higher rate.
    sess_variant = users.set_index("user_id").loc[sess_user, "ab_variant"].values
    p_buy = np.where(
        sess_variant == "treatment", P_PURCHASE * A_B_PURCHASE_LIFT, P_PURCHASE
    )
    purchase = checkout & (rng.random(N_SESSIONS) < p_buy)

    frames = []
    step_lag = {
        "app_open": 0,
        "view_item": 5,
        "add_to_cart": 15,
        "checkout": 40,
        "purchase": 90,
    }
    masks = {
        "app_open": np.ones(N_SESSIONS, dtype=bool),
        "view_item": view,
        "add_to_cart": cart,
        "checkout": checkout,
        "purchase": purchase,
    }
    for name, mask in masks.items():
        if not mask.any():
            continue
        frames.append(
            pd.DataFrame(
                {
                    "user_id": sess_user[mask],
                    "session_id": session_id[mask],
                    "event_time": sess_ts[mask]
                    + pd.to_timedelta(step_lag[name], unit="s"),
                    "event_name": name,
                }
            )
        )
    events = pd.concat(frames, ignore_index=True)
    events.insert(0, "event_id", np.arange(1, len(events) + 1))

    # Orders from purchase events.
    pur = events[events["event_name"] == "purchase"].copy()
    n_p = len(pur)
    amount = np.round(np.exp(rng.normal(3.2, 0.5, n_p)), 2)  # log-normal, ~$25 avg
    orders = pd.DataFrame(
        {
            "order_id": np.arange(1, n_p + 1),
            "user_id": pur["user_id"].values,
            "order_ts": pur["event_time"].values,
            "amount": amount,
            "product_category": rng.choice(PRODUCT_CATEGORIES, n_p),
        }
    )

    # Subscriptions: 30% of purchasing users convert, shortly after first purchase.
    purch_users = pur["user_id"].unique()
    n_sub = int(len(purch_users) * 0.30)
    sub_users = rng.choice(purch_users, n_sub, replace=False)
    plan = rng.choice(["monthly", "annual"], n_sub, p=[0.70, 0.30])
    sub_amount = np.where(plan == "monthly", 9.99, 89.99)
    first_order = orders.groupby("user_id")["order_ts"].min().reindex(sub_users).values
    started = pd.to_datetime(first_order) + pd.to_timedelta(
        rng.integers(0, 7 * 24 * 60, n_sub), unit="m"
    )
    started = np.minimum(started, END)  # subs cannot start after the window
    subscriptions = pd.DataFrame(
        {
            "sub_id": np.arange(1, n_sub + 1),
            "user_id": sub_users,
            "started_at": started,
            "plan": plan,
            "amount": sub_amount,
        }
    )
    return events, orders, subscriptions


def build_cancellations(
    rng: np.random.Generator, subscriptions: pd.DataFrame
) -> pd.DataFrame:
    """~40% of subscriptions cancel after start, within the observation window.

    Drawn from the seed-43 stream only; seed-42 tables stay identical.
    """
    n = len(subscriptions)
    mask = rng.random(n) < 0.40
    started = subscriptions["started_at"].values.astype("datetime64[ns]")
    cand = np.minimum(
        started + rng.integers(1, 61, n).astype("timedelta64[D]"),
        np.datetime64(END),
    )
    ok = mask & (cand > started)
    return pd.DataFrame(
        {
            "sub_id": subscriptions["sub_id"].values[ok],
            "cancelled_at": cand[ok],
        }
    )


def build_refunds(rng: np.random.Generator, orders: pd.DataFrame) -> pd.DataFrame:
    """~5% of orders are refunded shortly after purchase (full or half).

    Drawn from the seed-43 stream only; seed-42 tables stay identical.
    """
    n = len(orders)
    mask = rng.random(n) < 0.05
    ts = orders["order_ts"].values.astype("datetime64[ns]")
    frac = rng.choice([1.0, 0.5], n, p=[0.60, 0.40])
    amt = np.round(orders["amount"].values * frac, 2)
    cand = np.minimum(
        ts + rng.integers(0, 31, n).astype("timedelta64[D]"), np.datetime64(END)
    )
    oids = orders["order_id"].values[mask]
    return pd.DataFrame(
        {
            "refund_id": np.arange(1, len(oids) + 1),
            "order_id": oids,
            "refunded_at": cand[mask],
            "amount": amt[mask],
        }
    )


def write_outputs(users, events, orders, subscriptions, cancellations, refunds) -> None:
    HERE.joinpath("users.csv").write_text("")
    for name, df in [
        ("users", users),
        ("events", events),
        ("orders", orders),
        ("subscriptions", subscriptions),
        ("subscription_cancellations", cancellations),
        ("refunds", refunds),
    ]:
        df.to_csv(HERE / f"{name}.csv", index=False)

    db = HERE / "analytics.duckdb"
    if db.exists():
        db.unlink()
    con = duckdb.connect(str(db))
    con.execute(SCHEMA)
    con.register("_users", users)
    con.register("_events", events)
    con.register("_orders", orders)
    con.register("_subs", subscriptions)
    con.register("_canc", cancellations)
    con.register("_refunds", refunds)
    con.execute("INSERT INTO users SELECT * FROM _users")
    con.execute("INSERT INTO events SELECT * FROM _events")
    con.execute("INSERT INTO orders SELECT * FROM _orders")
    con.execute("INSERT INTO subscriptions SELECT * FROM _subs")
    con.execute("INSERT INTO subscription_cancellations SELECT * FROM _canc")
    con.execute("INSERT INTO refunds SELECT * FROM _refunds")
    for tbl in (
        "users",
        "events",
        "orders",
        "subscriptions",
        "subscription_cancellations",
        "refunds",
    ):
        print(
            f"  {tbl}: {con.execute(f'SELECT COUNT(*) FROM {tbl}').fetchone()[0]:,} rows"
        )
    # Real-data table for case 26 (UCI Online Retail II). Loaded when present so
    # the case runs against the same database as the synthetic cases.
    if REALDATA.exists():
        con.execute(
            f"CREATE TABLE online_retail AS SELECT * FROM read_parquet('{REALDATA}')"
        )
        print(
            "  online_retail (real, UCI Online Retail II): "
            f"{con.execute('SELECT COUNT(*) FROM online_retail').fetchone()[0]:,} rows"
        )
    con.close()


def main() -> None:
    rng = np.random.default_rng(SEED)
    rng_add = np.random.default_rng(SEED_ADDITIVE)
    print(f"Generating data (seed={SEED}, users={N_USERS}, sessions={N_SESSIONS})...")
    users = build_users(rng)
    events, orders, subscriptions = build_events(rng, users)
    cancellations = build_cancellations(rng_add, subscriptions)
    refunds = build_refunds(rng_add, orders)
    write_outputs(users, events, orders, subscriptions, cancellations, refunds)
    print(f"Done. CSVs + analytics.duckdb in {HERE}")


if __name__ == "__main__":
    main()
