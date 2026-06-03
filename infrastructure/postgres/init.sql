-- ===========================================================================
-- MCHPAI — PostgreSQL "truth database" schema.
-- Entities, relationships, scores, positions, fills. Time-series volume lives
-- in ClickHouse; the graph lives in Neo4j. This is the source of record.
-- ===========================================================================

CREATE SCHEMA IF NOT EXISTS mchpai;
SET search_path TO mchpai, public;

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- --------------------------------------------------------------------- tokens
CREATE TABLE IF NOT EXISTS tokens (
    mint              TEXT PRIMARY KEY,
    symbol            TEXT,
    name              TEXT,
    decimals          SMALLINT,
    creator           TEXT,
    source            TEXT,                  -- pumpfun | raydium | meteora | ...
    created_at        TIMESTAMPTZ,
    first_seen_slot   BIGINT,
    mint_authority    TEXT,
    freeze_authority  TEXT,
    lp_burned         BOOLEAN,
    metadata          JSONB DEFAULT '{}'::jsonb,
    risk_score        REAL,                  -- 0..100, latest
    updated_at        TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_tokens_creator ON tokens(creator);
CREATE INDEX IF NOT EXISTS idx_tokens_created_at ON tokens(created_at DESC);

-- -------------------------------------------------------------------- wallets
CREATE TABLE IF NOT EXISTS wallets (
    address           TEXT PRIMARY KEY,
    first_seen_at     TIMESTAMPTZ,
    first_funded_by   TEXT,                  -- funding ancestor (if known)
    label             TEXT,                  -- sniper | insider | mm | retail | bot
    tags              TEXT[] DEFAULT '{}',
    metadata          JSONB DEFAULT '{}'::jsonb,
    updated_at        TIMESTAMPTZ DEFAULT now()
);

-- Behavioral profile (rolling window snapshot; history in ClickHouse).
CREATE TABLE IF NOT EXISTS wallet_profiles (
    address            TEXT PRIMARY KEY REFERENCES wallets(address) ON DELETE CASCADE,
    window_days        INT NOT NULL DEFAULT 30,
    closed_trades      INT  DEFAULT 0,
    roi                REAL,                 -- realized PnL / cost basis
    win_rate           REAL,                 -- 0..1
    avg_hold_seconds   REAL,
    conviction         REAL,                 -- 0..1
    risk               REAL,                 -- 0..1 (behavioral risk appetite)
    profit_consistency REAL,                 -- 0..1
    realized_pnl_sol   REAL,
    computed_at        TIMESTAMPTZ DEFAULT now()
);

-- ------------------------------------------------------------------ trades
-- Normalized swaps (buys/sells). High-volume mirror lives in ClickHouse.
CREATE TABLE IF NOT EXISTS trades (
    id            BIGSERIAL PRIMARY KEY,
    signature     TEXT NOT NULL,
    wallet        TEXT NOT NULL,
    mint          TEXT NOT NULL,
    side          TEXT NOT NULL CHECK (side IN ('buy','sell')),
    sol_amount    DOUBLE PRECISION NOT NULL,
    token_amount  DOUBLE PRECISION NOT NULL,
    price_sol     DOUBLE PRECISION,
    program       TEXT,
    slot          BIGINT,
    block_time    TIMESTAMPTZ,
    UNIQUE (signature, wallet, mint, side)
);
CREATE INDEX IF NOT EXISTS idx_trades_wallet ON trades(wallet, block_time DESC);
CREATE INDEX IF NOT EXISTS idx_trades_mint   ON trades(mint, block_time DESC);

-- ------------------------------------------------------------------- scores
CREATE TABLE IF NOT EXISTS wallet_scores (
    address            TEXT PRIMARY KEY REFERENCES wallets(address) ON DELETE CASCADE,
    wallet_alpha_score REAL,                 -- 0..100
    components         JSONB DEFAULT '{}'::jsonb,
    computed_at        TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS clusters (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cluster_score REAL,                      -- 0..100
    size          INT,
    method        TEXT,                      -- louvain | cc | funding
    label         TEXT,
    detected_at   TIMESTAMPTZ DEFAULT now(),
    metadata      JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS cluster_members (
    cluster_id    UUID REFERENCES clusters(id) ON DELETE CASCADE,
    address       TEXT REFERENCES wallets(address) ON DELETE CASCADE,
    PRIMARY KEY (cluster_id, address)
);

-- ------------------------------------------------------------- predictions
CREATE TABLE IF NOT EXISTS predictions (
    id              BIGSERIAL PRIMARY KEY,
    mint            TEXT NOT NULL,
    model_version   TEXT,
    buy_probability REAL,                    -- 0..1
    expected_value  REAL,                    -- bps
    risk_score      REAL,                    -- 0..100
    features        JSONB DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_predictions_mint ON predictions(mint, created_at DESC);

-- ------------------------------------------------------------ execution
CREATE TABLE IF NOT EXISTS positions (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    mint          TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','closed','failed')),
    entry_sol     DOUBLE PRECISION,
    size_sol      DOUBLE PRECISION,
    token_amount  DOUBLE PRECISION,
    exit_sol      DOUBLE PRECISION,
    pnl_sol       DOUBLE PRECISION,
    opened_at     TIMESTAMPTZ DEFAULT now(),
    closed_at     TIMESTAMPTZ,
    source_signal BIGINT,
    metadata      JSONB DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_positions_status ON positions(status, opened_at DESC);

CREATE TABLE IF NOT EXISTS fills (
    id            BIGSERIAL PRIMARY KEY,
    position_id   UUID REFERENCES positions(id) ON DELETE CASCADE,
    signature     TEXT,
    side          TEXT CHECK (side IN ('buy','sell')),
    sol_amount    DOUBLE PRECISION,
    token_amount  DOUBLE PRECISION,
    landed_slot   BIGINT,
    jito_bundle   TEXT,
    latency_ms    INT,
    created_at    TIMESTAMPTZ DEFAULT now()
);

-- ------------------------------------------------------------------ leaderboard
CREATE TABLE IF NOT EXISTS leaderboard_snapshots (
    id            BIGSERIAL PRIMARY KEY,
    captured_at   TIMESTAMPTZ DEFAULT now(),
    rankings      JSONB NOT NULL              -- ordered [{address, score, ...}]
);
