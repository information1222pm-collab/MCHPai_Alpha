"""The Research Layer.

A place to *understand* wallets, not to act on them. There is deliberately:

* no production execution logic,
* no copy trading,
* no Jito / bundling,
* no position sizing,
* no trading decisions.

Each lab is a lens on the same observed reality:

* :mod:`wis.research.wallet_alpha_lab` — who, and how strongly, by alpha.
* :mod:`wis.research.cluster_lab` — community structure and its evolution.
* :mod:`wis.research.graph_lab` — funding trees, density, centrality.
* :mod:`wis.research.timing_lab` — entry/exit timing and patience.
* :mod:`wis.research.conviction_lab` — sizing, concentration, diamond hands.
* :mod:`wis.research.behavior_lab` — DNA trait distributions.
* :mod:`wis.research.sequence_lab` — the wallet as a movie, frame by frame.

Labs are pure read-side analyses over the :class:`~wis.app.observatory.Observatory`.
They return data, never orders.
"""
