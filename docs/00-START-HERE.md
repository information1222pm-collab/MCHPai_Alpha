# 00 — Start Here

Welcome back, Cloudi. This page is the map. Do things in this order and you won't
get overwhelmed.

## The mental model (read this first)

A Rogue at the SoR endgame is still the simplest melee DPS in the game:

> **Be behind the mob → keep Auto-Attack + Backstab running → fire burns on
> cooldown → don't stand in bad stuff.**

That's it. Every "complicated" thing you've seen is just a flavor of *"which
buttons fire during a burn, and in what order."* We've pre-built that order for
you. Your job becomes **positioning and timing**, not memorizing 40 abilities.

## Your bottlenecks, and where each is solved

| You said… | Fixed by… |
|-----------|-----------|
| "Too many buttons" | One burn key + one assist key. [`hotkeys/`](../hotkeys/) and [`macros/`](../macros/) |
| "DPS inconsistency" | Cooldown tracking + a fixed burn order so nothing is wasted. [`04-burn-and-cooldown-reference.md`](04-burn-and-cooldown-reference.md) + [`ui/`](../ui/) |
| "Don't know where to begin" | This file. Follow the steps below. |
| "Corpse recovery / swapping targets" | Dedicated labeled hotkeys. [`hotkeys/rogue-socials.txt`](../hotkeys/rogue-socials.txt) |

## Do this in order

### Step 1 — Read what changed (15 min)
[`01-whats-changed-since-omens.md`](01-whats-changed-since-omens.md)
A plain-English catch-up on what's new since Omens. No homework, just context so
the rest makes sense.

### Step 2 — Set up in-game hotkeys (20 min, no MQ2 needed)
[`hotkeys/rogue-socials.txt`](../hotkeys/rogue-socials.txt)
This gives you a working, simplified bar **today**. If you never touched MQ2,
you'd already be in much better shape than where you are now.

### Step 3 — Learn the rotation (read once, practice on a dummy/trash)
[`03-rogue-dps-rotation-and-positioning.md`](03-rogue-dps-rotation-and-positioning.md)
The "what fires when" — both for the hotkey version and the macro version.

### Step 4 — Install MQ2 and the burn macro (1 evening)
[`02-mq2-install-and-setup.md`](02-mq2-install-and-setup.md) →
[`macros/RogueBurn.mac`](../macros/RogueBurn.mac)
Now your burn is literally one key. This is the big DPS-consistency win.

### Step 5 — Wire in the Shaman (boxing)
[`05-shaman-box-coordination.md`](05-shaman-box-coordination.md)
Assist, slow, malo, haste, and rez — driven from your Rogue window.

### Step 6 — Track DPS and tune
[`06-dps-troubleshooting-checklist.md`](06-dps-troubleshooting-checklist.md) +
[`07-parsing-and-dps-meter.md`](07-parsing-and-dps-meter.md) +
[`ui/index.html`](../ui/index.html)
Parse yourself, find the leaks, close them. This is how you get *competitive*.

---

**If you only do one thing today:** Step 2. It's 20 minutes and it removes the
"too many buttons" problem immediately.
