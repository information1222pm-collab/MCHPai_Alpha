//! Final, defensive position sizing in the hot path.
//!
//! The Python strategy-engine does the rich fractional-Kelly sizing; this is a
//! last-line guard that re-applies a risk shrink and hard ceiling right before
//! signing, so a bad/stale upstream value can never blow the bankroll.

/// Apply a risk shrink and clamp. `risk_score` is 0..100 (higher = riskier).
pub fn final_size(requested_sol: f64, risk_score: f64) -> f64 {
    const HARD_MAX_SOL: f64 = 5.0;
    let risk_mult = (1.0 - (risk_score.clamp(0.0, 100.0) / 100.0)).max(0.0);
    let sized = requested_sol * risk_mult;
    sized.clamp(0.0, HARD_MAX_SOL)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn shrinks_for_risk() {
        assert!(final_size(1.0, 0.0) > final_size(1.0, 80.0));
    }

    #[test]
    fn respects_hard_max() {
        assert_eq!(final_size(100.0, 0.0), 5.0);
    }
}
