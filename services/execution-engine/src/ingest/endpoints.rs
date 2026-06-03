//! Endpoint pool with health-aware rotation for Yellowstone failover.
//!
//! Multiple Geyser providers are tried in round-robin; an endpoint that errors is
//! marked unhealthy and skipped, with exponential backoff before it is retried.
//! This keeps the ingest path alive across single-provider outages — the heart of
//! the system must never stop beating.

use std::sync::atomic::{AtomicBool, AtomicU32, AtomicUsize, Ordering};
use std::time::{Duration, Instant};

pub struct Endpoint {
    pub url: String,
    pub x_token: String,
    healthy: AtomicBool,
    fail_count: AtomicU32,
    cooldown_until: parking_lot_stub::Mutex<Option<Instant>>,
}

impl Endpoint {
    pub fn new(url: String, x_token: String) -> Self {
        Endpoint {
            url,
            x_token,
            healthy: AtomicBool::new(true),
            fail_count: AtomicU32::new(0),
            cooldown_until: parking_lot_stub::Mutex::new(None),
        }
    }

    pub fn is_available(&self) -> bool {
        if self.healthy.load(Ordering::Relaxed) {
            return true;
        }
        // unhealthy: available again only after the cooldown elapses
        let guard = self.cooldown_until.lock();
        matches!(*guard, Some(t) if Instant::now() >= t)
    }

    pub fn mark_ok(&self) {
        self.healthy.store(true, Ordering::Relaxed);
        self.fail_count.store(0, Ordering::Relaxed);
        *self.cooldown_until.lock() = None;
    }

    pub fn mark_failed(&self) {
        let fails = self.fail_count.fetch_add(1, Ordering::Relaxed) + 1;
        self.healthy.store(false, Ordering::Relaxed);
        // exponential backoff capped at 60s: 1,2,4,8,...
        let secs = (1u64 << fails.min(6)).min(60);
        *self.cooldown_until.lock() = Some(Instant::now() + Duration::from_secs(secs));
    }
}

pub struct EndpointPool {
    endpoints: Vec<Endpoint>,
    cursor: AtomicUsize,
}

impl EndpointPool {
    pub fn new(pairs: Vec<(String, String)>) -> Self {
        EndpointPool {
            endpoints: pairs.into_iter().map(|(u, t)| Endpoint::new(u, t)).collect(),
            cursor: AtomicUsize::new(0),
        }
    }

    pub fn is_empty(&self) -> bool {
        self.endpoints.is_empty()
    }

    pub fn len(&self) -> usize {
        self.endpoints.len()
    }

    /// Round-robin to the next currently-available endpoint, if any.
    pub fn next_available(&self) -> Option<&Endpoint> {
        let n = self.endpoints.len();
        if n == 0 {
            return None;
        }
        for _ in 0..n {
            let i = self.cursor.fetch_add(1, Ordering::Relaxed) % n;
            if self.endpoints[i].is_available() {
                return Some(&self.endpoints[i]);
            }
        }
        None
    }
}

/// Tiny dependency-free mutex shim so this module needs no extra crates.
mod parking_lot_stub {
    use std::sync::{Mutex as StdMutex, MutexGuard};

    pub struct Mutex<T>(StdMutex<T>);
    impl<T> Mutex<T> {
        pub fn new(v: T) -> Self {
            Mutex(StdMutex::new(v))
        }
        pub fn lock(&self) -> MutexGuard<'_, T> {
            self.0.lock().unwrap_or_else(|e| e.into_inner())
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn rotates_and_skips_unhealthy() {
        let pool = EndpointPool::new(vec![
            ("a".into(), "".into()),
            ("b".into(), "".into()),
        ]);
        let first = pool.next_available().unwrap();
        first.mark_failed(); // a now unhealthy
        // next_available should now return the healthy one repeatedly
        for _ in 0..4 {
            assert_eq!(pool.next_available().unwrap().url, "b");
        }
    }

    #[test]
    fn recovers_after_mark_ok() {
        let pool = EndpointPool::new(vec![("a".into(), "".into())]);
        let e = pool.next_available().unwrap();
        e.mark_failed();
        assert!(pool.next_available().is_none()); // in cooldown
        e.mark_ok();
        assert!(pool.next_available().is_some());
    }
}
