"""MCHPAI shared library.

The contract layer of the platform. Everything services depend on lives here:
versioned domain **schemas**, the **events** that flow over NATS JetStream,
datastore **clients**, structured **logging**, **metrics**, and the first-class
**domain sciences** (entropy, epidemiology, ecology, astronomy, battlefield,
forecasting).

Import surface is intentionally small and stable; submodules are imported
explicitly to keep cold-start fast.
"""

__version__ = "0.1.0"
