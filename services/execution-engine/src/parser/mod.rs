//! Transaction parsing: decode DEX instructions into normalized swap events.

pub mod swap;

// Re-exported for downstream consumers (real Yellowstone parser wiring); the
// skeleton publisher references the fully-qualified path, so allow until used.
#[allow(unused_imports)]
pub use swap::{SwapEvent, SwapSide};
