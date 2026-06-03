// ===========================================================================
// MCHPAI — Neo4j graph intelligence bootstrap.
// Nodes: Wallet, Token, Cluster. Edges: FUNDED, TRANSFERRED, BOUGHT,
// CO_BOUGHT, IN_CLUSTER. Run via `make migrate`.
// ===========================================================================

// ---- Constraints (also create backing indexes) ----
CREATE CONSTRAINT wallet_address IF NOT EXISTS
  FOR (w:Wallet) REQUIRE w.address IS UNIQUE;

CREATE CONSTRAINT token_mint IF NOT EXISTS
  FOR (t:Token) REQUIRE t.mint IS UNIQUE;

CREATE CONSTRAINT cluster_id IF NOT EXISTS
  FOR (c:Cluster) REQUIRE c.id IS UNIQUE;

// ---- Secondary indexes for traversal hot paths ----
CREATE INDEX wallet_alpha IF NOT EXISTS FOR (w:Wallet) ON (w.alpha_score);
CREATE INDEX token_created IF NOT EXISTS FOR (t:Token) ON (t.created_at);

// ---- Reference of the relationship model (documentation only) ----
// (:Wallet)-[:FUNDED {sol, ts}]->(:Wallet)
// (:Wallet)-[:TRANSFERRED {amount, mint, ts}]->(:Wallet)
// (:Wallet)-[:BOUGHT {mint, ts, sol}]->(:Token)
// (:Wallet)-[:CO_BOUGHT {mint, dt_seconds}]->(:Wallet)
// (:Wallet)-[:IN_CLUSTER]->(:Cluster {id, score})
