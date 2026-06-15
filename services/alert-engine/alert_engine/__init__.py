"""alert-engine — fan-out notifications to humans.

Subscribes to high-value signals (buy signals, cluster detections, attention
spikes) and dispatches to configured channels (Discord, Telegram, Email,
Webhooks). Channels are pluggable; unconfigured channels are silently skipped.
"""
