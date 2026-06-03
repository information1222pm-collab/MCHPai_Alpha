//! Slot reconciliation & replay.
//!
//! Stream uptime is never 100%: providers hiccup, connections drop, slots get
//! missed. The reconciler turns detected gaps (from [`SlotTracker`]) into
//! [`BackfillRequest`]s that a backfiller fulfills via RPC (`getBlock`), so the
//! `raw.swaps` stream is *eventually complete* even across outages. Combined with
//! the durable Redis stream (consumers replay from their last ack), this is how
//! we approach 99.99% effective coverage.

use super::slot::SlotUpdate;

/// A contiguous range of slots that must be backfilled out-of-band.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct BackfillRequest {
    pub from_slot: u64, // inclusive
    pub to_slot: u64,   // inclusive
}

impl BackfillRequest {
    pub fn count(&self) -> u64 {
        self.to_slot.saturating_sub(self.from_slot) + 1
    }
}

#[derive(Default)]
pub struct Reconciler {
    last: u64,
    max_gap_backfill: u64, // cap to avoid pathological backfills on cold start
}

impl Reconciler {
    pub fn new(max_gap_backfill: u64) -> Self {
        Reconciler { last: 0, max_gap_backfill }
    }

    /// Feed an observed slot update; returns a backfill request if a gap opened.
    pub fn observe(&mut self, update: SlotUpdate) -> Option<BackfillRequest> {
        if !update.advanced {
            return None; // stale/duplicate — nothing to reconcile
        }
        let prev = self.last;
        self.last = update.slot;
        if update.gap == 0 || prev == 0 {
            return None;
        }
        let missing = update.gap.min(self.max_gap_backfill);
        let from = update.slot - missing - 1 + 1; // first missed slot
        Some(BackfillRequest { from_slot: from, to_slot: update.slot - 1 })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::ingest::slot::SlotTracker;

    #[test]
    fn emits_backfill_on_gap() {
        let tracker = SlotTracker::new();
        let mut rec = Reconciler::new(1000);
        rec.observe(tracker.observe(100)); // first, no gap
        let req = rec.observe(tracker.observe(105)).unwrap();
        assert_eq!(req.from_slot, 101);
        assert_eq!(req.to_slot, 104);
        assert_eq!(req.count(), 4);
    }

    #[test]
    fn no_backfill_when_contiguous() {
        let tracker = SlotTracker::new();
        let mut rec = Reconciler::new(1000);
        rec.observe(tracker.observe(100));
        assert!(rec.observe(tracker.observe(101)).is_none());
    }

    #[test]
    fn caps_huge_gaps() {
        let tracker = SlotTracker::new();
        let mut rec = Reconciler::new(10);
        rec.observe(tracker.observe(100));
        let req = rec.observe(tracker.observe(10_000)).unwrap();
        assert_eq!(req.count(), 10); // capped
    }
}
