"""Tests for the Feature Factory (spec → compiler → features)."""

from mchpai_common.feature_factory import (
    FeatureCompiler,
    FeatureContext,
    FeatureSpec,
    Normalization,
    build_default_catalog,
)


def test_passthrough_and_ratio():
    specs = [
        FeatureSpec(name="p", transform="input", dependencies=("price_sol",)),
        FeatureSpec(name="bs", transform="ratio", dependencies=("buyers", "sellers")),
    ]
    c = FeatureCompiler(specs)
    out = c.compute(FeatureContext(inputs={"price_sol": 2.0, "buyers": 10, "sellers": 5}))
    assert out["p"] == 2.0
    assert out["bs"] == 2.0


def test_rolling_window_uses_history():
    spec = [FeatureSpec(name="ma", transform="rolling_mean", dependencies=("v",), window=3)]
    c = FeatureCompiler(spec)
    ctx = FeatureContext(inputs={"v": 4.0}, history=[{"v": 1.0}, {"v": 2.0}, {"v": 3.0}])
    out = c.compute(ctx)
    assert out["ma"] == 3.0  # mean of last 3: [2,3,4]


def test_derived_of_derived_topo_order():
    specs = [
        FeatureSpec(name="short", transform="rolling_mean", dependencies=("price",), window=2),
        FeatureSpec(name="long", transform="rolling_mean", dependencies=("price",), window=5),
        FeatureSpec(name="momentum", transform="diff", dependencies=("short", "long")),
    ]
    c = FeatureCompiler(specs)
    # momentum must be computed after short & long
    assert c.feature_names.index("momentum") > c.feature_names.index("short")
    rows = [{"price": p} for p in (1, 2, 3, 4, 5)]
    out = c.compute(FeatureContext(inputs=rows[-1], history=rows[:-1]))
    assert "momentum" in out


def test_cycle_detection():
    specs = [
        FeatureSpec(name="a", transform="input", dependencies=("b",)),
        FeatureSpec(name="b", transform="input", dependencies=("a",)),
    ]
    try:
        FeatureCompiler(specs)
        assert False, "expected cycle error"
    except ValueError as e:
        assert "cycle" in str(e)


def test_normalization_applied():
    spec = [FeatureSpec(name="z", transform="input", dependencies=("x",),
                        normalization=Normalization.tanh)]
    c = FeatureCompiler(spec)
    out = c.compute(FeatureContext(inputs={"x": 100.0}))
    assert abs(out["z"] - 1.0) < 1e-6  # tanh(100) ≈ 1


def test_default_catalog_scales():
    specs = build_default_catalog()
    # combinatorial generation should yield hundreds of features from a few rules
    assert len(specs) > 100
    names = {s.name for s in specs}
    assert len(names) == len(specs)  # all unique
    c = FeatureCompiler(specs)  # must form a valid DAG
    # compute a full sequence end-to-end
    rows = [
        {"price_sol": 1.0 + i * 0.1, "volume_sol": 10 + i, "buyers": 5 + i, "sellers": 2,
         "liquidity_sol": 100, "market_cap_sol": 1000, "unique_traders": 6, "holders": 50,
         "txns": 8, "net_flow_sol": 3.0, "entropy": 0.5, "smart_money_ratio": 0.3,
         "cluster_ratio": 0.1}
        for i in range(25)
    ]
    seq = c.compute_sequence(rows)
    assert len(seq) == 25
    assert len(seq[-1]) == len(specs)  # every feature produced at every step


def test_compute_sequence_windowing_is_causal():
    spec = [FeatureSpec(name="msum", transform="rolling_sum", dependencies=("v",), window=10)]
    c = FeatureCompiler(spec)
    rows = [{"v": 1.0}, {"v": 1.0}, {"v": 1.0}]
    seq = c.compute_sequence(rows)
    # step 0 sees only itself, step 2 sees all three (no future leakage)
    assert seq[0]["msum"] == 1.0
    assert seq[2]["msum"] == 3.0
