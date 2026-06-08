"""The reproducibility statistics must be honest at small n and degrade
gracefully — confidence intervals are humility, quantified."""

from __future__ import annotations

import math

from wis.research.reality_lab.reproduce import summarize, wilson_interval


def test_wilson_interval_basic_bounds() -> None:
    assert wilson_interval(0, 0) == (0.0, 1.0)  # no data → maximal uncertainty
    lo, hi = wilson_interval(50, 100)
    assert lo < 0.5 < hi and lo > 0.3 and hi < 0.7  # reasonably tight at n=100
    # Stays within [0, 1] and is wide at small n.
    lo, hi = wilson_interval(1, 5)
    assert 0.0 <= lo < hi <= 1.0
    assert hi - lo > 0.4  # genuinely uncertain


def test_summarize_single_trial_has_no_width() -> None:
    s = summarize([0.59], [4000])
    assert s.n_trials == 1
    assert s.ci_lo == s.ci_hi == 0.59


def test_summarize_multiple_trials() -> None:
    s = summarize([0.56, 0.59, 0.61, 0.58, 0.60], [1000, 1100, 900, 1200, 1050])
    assert s.n_trials == 5
    assert math.isclose(s.mean, 0.588, abs_tol=1e-9)
    assert s.ci_lo < s.mean < s.ci_hi
    assert s.std > 0
    assert not s.low_confidence  # 5 trials, pooled n large


def test_summarize_flags_low_confidence() -> None:
    # Few trials / tiny pooled denominator → flagged.
    s = summarize([0.2, 0.25], [5, 8])
    assert s.low_confidence
    assert "⚠" in s.as_pct()
