-- ===========================================================================
-- MCHPAI — ClickHouse schema: high-volume time-series & analytics.
-- Postgres holds the truth; ClickHouse holds the firehose (snapshots, every
-- swap, feature vectors) for fast analytical scans and model training pulls.
-- ===========================================================================

CREATE DATABASE IF NOT EXISTS mchpai;

-- Every observed swap (append-only firehose).
CREATE TABLE IF NOT EXISTS mchpai.trades
(
    block_time   DateTime64(3),
    slot         UInt64,
    signature    String,
    wallet       String,
    mint         String,
    side         Enum8('buy' = 1, 'sell' = 2),
    sol_amount   Float64,
    token_amount Float64,
    price_sol    Float64,
    program      LowCardinality(String)
)
ENGINE = MergeTree
PARTITION BY toYYYYMMDD(block_time)
ORDER BY (mint, block_time, wallet)
TTL toDateTime(block_time) + INTERVAL 180 DAY;

-- Periodic token market snapshots (price/liquidity/holders).
CREATE TABLE IF NOT EXISTS mchpai.token_snapshots
(
    ts            DateTime64(3),
    mint          String,
    price_sol     Float64,
    price_usd     Float64,
    liquidity_sol Float64,
    market_cap    Float64,
    holders       UInt32,
    volume_1m     Float64,
    buys_1m       UInt32,
    sells_1m      UInt32,
    source        LowCardinality(String)
)
ENGINE = MergeTree
PARTITION BY toYYYYMMDD(ts)
ORDER BY (mint, ts);

-- Materialized feature vectors emitted by feature-engine (for training/serving).
CREATE TABLE IF NOT EXISTS mchpai.feature_vectors
(
    ts          DateTime64(3),
    entity_type Enum8('token' = 1, 'wallet' = 2, 'cluster' = 3),
    entity_id   String,
    feature_set LowCardinality(String),   -- creator | liquidity | entropy | spread | attention
    features    Map(String, Float64)
)
ENGINE = MergeTree
PARTITION BY toYYYYMMDD(ts)
ORDER BY (entity_type, entity_id, ts);

-- Multi-resolution token snapshots — the ordered life-sequence of every token.
-- This is the Phase-1 "gold": 5s/15s/30s/60s steps with market + participation +
-- intelligence + safety metrics, ordered by (mint, window, ts) for sequence pulls.
CREATE TABLE IF NOT EXISTS mchpai.snapshots
(
    ts            DateTime64(3),
    mint          String,
    window        LowCardinality(String),   -- 5s | 15s | 30s | 60s
    seq           UInt64,
    age_seconds   Float64,
    phase         LowCardinality(String),   -- birth|growth|viral|distribution|death
    -- market
    price_sol     Float64,
    open_sol      Float64,
    high_sol      Float64,
    low_sol       Float64,
    close_sol     Float64,
    volume_sol    Float64,
    liquidity_sol Float64,
    market_cap_sol Float64,
    -- participation
    buyers        UInt32,
    sellers       UInt32,
    unique_traders UInt32,
    holders       UInt32,
    txns          UInt32,
    -- intelligence
    entropy            Float64,
    r0                 Float64,
    smart_money_ratio  Float64,
    cluster_ratio      Float64,
    net_flow_sol       Float64,
    -- safety
    top_holder_pct             Float64,
    holder_concentration_gini  Float64,
    lp_health                  Float64
)
ENGINE = MergeTree
PARTITION BY toYYYYMMDD(ts)
ORDER BY (mint, window, ts);

-- Attention / contagion telemetry (epidemiology + astronomy libs).
CREATE TABLE IF NOT EXISTS mchpai.attention
(
    ts            DateTime64(3),
    mint          String,
    attention     Float64,    -- normalized "mass"/infection pressure
    velocity      Float64,    -- d(attention)/dt
    entropy       Float64,    -- information content of the flow
    r0            Float64     -- epidemiological reproduction estimate
)
ENGINE = MergeTree
PARTITION BY toYYYYMMDD(ts)
ORDER BY (mint, ts);
