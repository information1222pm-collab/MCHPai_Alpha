"""strategy-engine — converts buy signals into sized, risk-checked orders.

Owns the portfolio's risk budget: fractional-Kelly position sizing, per-token and
per-day exposure caps, and the global kill-switch. Emits an ``Order`` (subject
``mchpai.exec.order``) that the Rust execution-engine acts on. Never signs
anything itself.
"""
