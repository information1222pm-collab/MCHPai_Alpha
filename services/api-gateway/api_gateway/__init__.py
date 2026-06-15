"""api-gateway — the read/control surface of the platform.

FastAPI app exposing REST endpoints (wallets, clusters, tokens, signals,
positions, discovery, leaderboard) and a WebSocket live feed bridged from NATS.
This is what the MCHPAI plugin UI talks to. Reads from Postgres/Redis/Neo4j;
control endpoints (pause/resume) flip Redis kill-switch flags.
"""
