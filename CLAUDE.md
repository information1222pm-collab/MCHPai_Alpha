# CLAUDE.md

Guidance for AI assistants (and humans) working in this repository.

## What this is

**MCHPAI** (a.k.a. "MCHPai Trench") is a **single-file, browser-based Solana
trading terminal** — an autonomous memecoin sniper and copy-trading bot with a
live observation dashboard. The entire application is **one self-contained HTML
file**: markup, CSS, and all JavaScript are inlined into a single document that
runs directly in a browser with **no build step, no server, and no package
manager**.

- Latest working artifact: `MCHPAI_rt293.html` (~28k lines, ~6 MB). Build
  version is tracked by an `rt-NNN` number that increments with every change
  (see [Build markers](#build-markers-rt-nnn)).
- The app trades on **Solana mainnet** via Helius RPC + Jupiter, with a
  **paper-trading mode** that models fills without spending real funds and a
  **LIVE mode** gated behind additional safety checks.
- Everything the user configures (API keys, strategies, follow lists, the
  learning "brain") lives **only in the browser** (`localStorage` /
  `sessionStorage` / IndexedDB). Nothing is committed to the repo.

> If you are asked to "run" or "test" the app, just open the HTML file in a
> modern browser. There is nothing to compile or install.

## Repository layout & the deploy convention

This repo is intentionally sparse. At rest it typically contains only:

```
README.md      # one line: "# MCHPai_Alpha"
CLAUDE.md      # this file
```

The application HTML is **not permanently tracked on the default branch**. The
established workflow (visible in git history) is:

1. A new versioned build is produced as `MCHPAI_rt<NNN>.html` (older builds used
   names like `trench_v78f_sprint5_complete.html`).
2. To deploy, that file is uploaded and **renamed to `index.html`** so it serves
   as a GitHub Pages entry point.
3. It is later deleted again, leaving the repo clean between deploys.

So the **canonical artifact is the versioned `*_rt<NNN>.html` file**, and
`index.html` is only ever a renamed copy of the current build. When a newer build
is provided (e.g. attached in a session), treat that as the source of truth —
its `rt-NNN` supersedes anything in git history.

### Git / branch workflow

- Do all development on the assigned feature branch; never push to `main`
  without explicit permission.
- Push with `git push -u origin <branch>`; retry network failures with
  exponential backoff.
- Do **not** open a pull request unless explicitly asked.

## How to work with the single-file app

Because the whole program is one file, normal "find the module" navigation does
not apply. Instead:

- **Locate subsystems by their `rt-NNN` marker or ALL-CAPS codename.** Almost
  every feature is introduced by a banner comment like
  `rt-239 RENDERGATE - memoized innerHTML ...`. Grep for the codename
  (`RENDERGATE`, `SMARTGATE`, `SENTRYGUARD`, `EXITRETRY`, …) to jump straight to
  the relevant block. This is the primary way to navigate the file.
- **Edit in place, surgically.** With ~28k lines and ~1,175 functions in one
  document, make the smallest change that works and keep it near the code it
  affects. Match the surrounding dense, minified-by-hand style (short names,
  packed one-liners, `try{}catch(_e){}` guards everywhere).
- **Preserve the inline-comment changelog.** The `rt-NNN` banner comments are
  the project's design log and history — they explain *why* a guard exists and
  what incident it prevents. When you change behavior a marker describes, update
  or extend that marker (bump to a new `rt-NNN` when appropriate) rather than
  deleting the rationale.
- **Never break the "no external build" constraint.** Dependencies are loaded
  from CDNs at runtime or inlined (e.g. `bs58` is hand-inlined to avoid a CDN
  dependency). Do not introduce a bundler, npm install, or local module imports.

### File structure inside the HTML

Top-to-bottom the document is roughly:

1. `<head>` — meta, title, and a few **early inline `<script>` guards that must
   run before anything else**:
   - `SENTRYGUARD` (rt-207) — defines `window.sentryOnLoad` / scrubbing **before**
     the Sentry loader tag so API keys never leak into error reports.
   - The **Sentry loader** (`js.sentry-cdn.com/...min.js`) — DSN
     `mchpai/javascript` (rt-208 verified the key end-to-end).
   - `RENDERGATE` (rt-239) — overrides `Element.prototype.innerHTML` with a
     memoizing setter to skip no-op DOM writes (biggest main-thread saver).
2. `<style>` — all CSS (Space Mono / Syne fonts, dark "trench" theme).
3. `<body>` — ~25 `<section id=s-...>` panels (the dashboard UI) plus a key-entry
   overlay. Sections include `s-trade`, `s-copy`, `s-opps`, `s-wallets`,
   `s-signals`, `s-patterns`, `s-intel`, `s-analytics`, `s-journal`,
   `s-mission`, `s-livemap`, `s-data`, and more.
4. Multiple large `<script>` blocks — the engine: RPC layer, ML/scoring,
   execution, risk systems, UI renderers, and the boot sequence
   (`DOMContentLoaded` → `boot()`).

## Runtime architecture (mental model)

- **Signer web worker** — transactions are signed off the main thread in a Blob
  worker (`signTxAsync`), falling back to synchronous signing. The private key is
  loaded into the worker from `sessionStorage`.
- **RPC layer** (`rpc(method, params)`) — sends go to the canonical
  `mainnet.helius-rpc.com` / `sender.helius-rpc.com`; some reads use a faster
  Helius edge host. The API key is appended as `?api-key=...` (this is exactly
  why `SENTRYGUARD` scrubs outbound URLs).
- **Data feeds** — Jupiter (`lite-api.jup.ag` / `api.jup.ag`) for quotes/swaps,
  DexScreener and RugCheck for token metadata/security, plus optional LLM calls
  to xAI Grok (`api.x.ai/v1/chat/completions`) for narrative/intel features.
- **Storage**
  - IndexedDB database **`mchpai`** with object stores: `swaps`, `trades`,
    `events`, `ledger`, `quotes`.
  - `localStorage` — config and learned state under `mchpai_*` keys (e.g.
    `mchpai_strats`, `mchpai_follows`, `mchpai_brain`, `mchpai_journal`,
    `mchpai_risk`, `mchpai_darwin`, `mchpai_livecfg`), plus `helius_key`,
    `cap_url`/`cap_token`.
  - `sessionStorage` — the private key (`mchpai_privkey`), never persisted to
    disk-backed storage.
- **Loops** — ~106 `setInterval` timers drive polling, repainting, and the
  autonomous trading cadence. RENDERGATE exists specifically to make these cheap.
- **Paper vs LIVE**
  - Paper mode models every entry/exit (fill, slippage, fee, proceeds) against
    real quotes without spending funds.
  - LIVE mode adds gates. Notably **`SMARTGATE` (rt-107): real money only enters
    a token that contains ≥1 validated "smart money" wallet** (or an explicit
    copy-wallet entry) — the backtested edge. Paper trades everything; live is
    deliberately narrower. `liveReadiness(S)` / `logWhyPaper(S)` explain why a
    signal stayed paper.
- **Portable snapshot** — `exportSettings()` / import wraps *all* local
  settings + brain + key into a versioned, migrate-forward envelope (optionally
  PBKDF2→AES-GCM encrypted) so a user can move builds/devices without losing
  setup.
- **Diagnostic export** — `exportData()` and the diag line are designed to be
  **pasted to a stranger**: they must never contain secrets. This "assume the
  payload is readable by anyone" doctrine is why the Sentry scrubbing and export
  paths are so defensive.

## Build markers (`rt-NNN`)

The `rt-NNN <CODENAME>` comments are the closest thing to a changelog and module
map this codebase has. A few load-bearing ones:

| Marker | Codename | Purpose |
| --- | --- | --- |
| rt-207 | `SENTRYGUARD` | Scrub/drop secrets before Sentry sends anything |
| rt-208 | `DSNFIX` | Correct, verified Sentry DSN/loader key |
| rt-239 | `RENDERGATE` | Memoized `innerHTML` to skip no-op repaints |
| rt-107 | `SMARTGATE` | LIVE entries require smart-money presence |
| rt-129 | `KEYPURGE` | No hardcoded keys; key lives only in `localStorage` |
| rt-150 | `EXITRETRY` | Escalating-delay retries for final exits only |
| rt-268 | `DARWIN` / rt-272 `DARWINLIVE` | Self-tuning wallet/strategy selection |
| rt-293 | `SWAPDUST` | Current head build |

There are **hundreds** of these (from `rt-35` up to `rt-293`). When investigating
behavior, grep the codename first — the comment usually names the exact incident
the code defends against.

## Conventions & guardrails

- **Secrets never leave the browser.** Keys are entered at runtime, stored in
  `localStorage`/`sessionStorage`, and only ever sent to their own provider
  (Helius, Jupiter, xAI). Any code path that could ship a key to a third party
  (error reporting, diagnostics, exports) must scrub or drop it. Do not weaken
  `SENTRYGUARD`, add breadcrumb integrations that capture URLs/fetch bodies with
  keys, or log full RPC URLs.
- **Fail soft.** The house style wraps risky operations in
  `try{...}catch(_e){}` and degrades gracefully rather than throwing — the app
  must keep trading/observing even when one feed or feature errors.
- **Paper truth must equal chain truth.** Much of the complexity exists to make
  the paper model's arithmetic agree with real on-chain fills. When touching
  execution/accounting, keep the paper and live paths consistent and ledger any
  divergence (see the `PARTX`/`EDGEBAND`/`LEDGERKEEP` markers).
- **Live trading is real money.** Default to the safe/paper path. Do not loosen
  risk gates (circuit breakers, `SMARTGATE`, sizing, cooldowns) or enable live
  execution without explicit user intent.
- **Keep it one file, dependency-light.** No new build tooling; prefer inlining
  over adding CDN dependencies.

## Common tasks

- **Find a feature:** grep the codename or `rt-NNN` marker.
- **Change UI:** locate the `<section id=s-...>` and its renderer function; note
  RENDERGATE means identical HTML strings are skipped — call
  `RENDERGATE.raw(el, html)` if you must force a repaint.
- **Add a data source:** add the host to the runtime fetch layer and confirm no
  secret rides in the URL/body that Sentry could capture.
- **Ship a build:** produce `MCHPAI_rt<NNN+1>.html`, bump the build tag, and (on
  request) rename to `index.html` for GitHub Pages deploy.
