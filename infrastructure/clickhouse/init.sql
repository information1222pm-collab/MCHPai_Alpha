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
