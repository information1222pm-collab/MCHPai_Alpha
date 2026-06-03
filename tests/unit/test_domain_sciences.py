"""Unit tests for the first-class domain-science libraries."""

import numpy as np

from mchpai_common import astronomy, ecology, entropy, epidemiology, forecasting, indicators


def test_entropy_uniform_is_max():
    assert entropy.normalized_entropy([1, 1, 1, 1]) == 1.0
    assert entropy.normalized_entropy([1]) == 0.0


def test_buyer_entropy_concentrated_is_low():
    concentrated = {"a": 99.0, "b": 1.0}
    diverse = {"a": 1.0, "b": 1.0, "c": 1.0, "d": 1.0}
    assert entropy.buyer_entropy(concentrated) < entropy.buyer_entropy(diverse)


def test_r0_growth():
    growing = np.array([1, 2, 4, 8, 16], dtype=float)
    assert epidemiology.estimate_r0(growing) > 1.0


def test_gravitational_pull_monotonic():
    near = astronomy.gravitational_pull(10, 100, distance=1.0)
    far = astronomy.gravitational_pull(10, 100, distance=10.0)
    assert near > far


def test_ecology_phase_classification():
    assert ecology.predator_prey_phase(10, 5) == "predator_dominant"
    assert ecology.predator_prey_phase(1, 100) == "prey_dominant"


def test_expected_value_sign():
    assert forecasting.expected_value(0.9, 600, 350) > 0
    assert forecasting.expected_value(0.1, 600, 350) < 0


def test_indicator_imbalance():
    assert indicators.imbalance(10, 0) == 1.0
    assert indicators.imbalance(0, 10) == -1.0
    assert indicators.imbalance(5, 5) == 0.0
