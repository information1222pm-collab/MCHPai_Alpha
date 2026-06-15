//! Slot tracking — monotonic progress + gap detection across the Geyser stream.
//!
//! Yellowstone delivers updates tagged with their slot. We track the highest slot
//! seen, detect gaps (missed slots ⇒ possible provider lag or reconnect), and
//! expose both for metrics/alerting. Gap awareness lets the system know when its
//! view of the chain is incomplete and trigger a catch-up/failover.

use std::sync::atomic::{AtomicU64, Ordering};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct SlotUpdate {
    pub slot: u64,
    pub advanced: bool, // strictly greater than the previous max
    pub gap: u64,       // slots skipped since the last observed slot (0 if contiguous)
    pub stale: bool,    // slot <= previous max (out-of-order / duplicate)
}

#[derive(Default)]
pub struct SlotTracker {
    last: AtomicU64,
    total_gaps: AtomicU64,
    max_gap: AtomicU64,
}

impl SlotTracker {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn observe(&self, slot: u64) -> SlotUpdate {
        let prev = self.last.load(Ordering::Relaxed);
        if prev == 0 {
            self.last.store(slot, Ordering::Relaxed);
            return SlotUpdate { slot, advanced: true, gap: 0, stale: false };
        }
        if slot <= prev {
            return SlotUpdate { slot, advanced: false, gap: 0, stale: true };
        }
        let gap = slot - prev - 1;
        self.last.store(slot, Ordering::Relaxed);
        if gap > 0 {
            self.total_gaps.fetch_add(gap, Ordering::Relaxed);
            self.max_gap.fetch_max(gap, Ordering::Relaxed);
        }
        SlotUpdate { slot, advanced: true, gap, stale: false }
    }

    pub fn last_slot(&self) -> u64 {
        self.last.load(Ordering::Relaxed)
    }

    pub fn total_gaps(&self) -> u64 {
        self.total_gaps.load(Ordering::Relaxed)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn detects_contiguous_and_gaps() {
        let t = SlotTracker::new();
        assert_eq!(t.observe(100).gap, 0);
        assert_eq!(t.observe(101).gap, 0);
        let u = t.observe(105);
        assert_eq!(u.gap, 3);
        assert!(u.advanced);
        assert_eq!(t.total_gaps(), 3);
    }

    #[test]
    fn flags_stale_slots() {
        let t = SlotTracker::new();
        t.observe(100);
        let u = t.observe(99);
        assert!(u.stale);
        assert!(!u.advanced);
        assert_eq!(t.last_slot(), 100);
    }
}
