# Cloudi's Rogue DPS Package — Shattering of Ro (Level 130)

A complete, no-fluff DPS optimization kit for a **returning EverQuest Rogue** who
last played seriously in *Omens of War* and is jumping back in at the
**Shattering of Ro (SoR)** endgame. Built for **end-game grouping and raiding**,
boxed alongside a **Shaman**, with a **raid-oriented, minimalist, dark-blue**
aesthetic.

> **Character:** Cloudi · Tunare · Rogue (130, full AAs) + Shaman box
> **Goal:** Maximum DPS, raid efficiency, less stress, competitive parses —
> *optimally, efficiently, and effortlessly.*

---

## Why this exists

You said it best: *"I just don't know where to begin anymore."* The game added a
decade-plus of disciplines, AAs, and combat abilities since Omens. The fix is not
"learn 200 buttons" — it's to **collapse the whole rotation into 2–3 keys** and a
HUD that shows you what's ready. That's exactly what this package does.

**The whole job of a Rogue is simple:** stay behind the mob, keep auto-attack and
Backstab going, and fire your burns when it counts. Everything here automates the
busywork so you can focus on staying behind the target and not dying.

---

## What's in the box

| Folder | What it is | Start here if you want… |
|--------|-----------|--------------------------|
| **[`docs/`](docs/)** | Step-by-step guides written for a returning player | …to understand *why*, not just *what* |
| **[`macros/`](macros/)** | Ready-to-run MQ2 macros — one-key burn, sustained assist, box coordination | …to press one key and do damage |
| **[`hotkeys/`](hotkeys/)** | Copy-paste in-game social hotkeys (no MQ2 needed) | …a setup that works *today* before you learn MQ2 |
| **[`ui/`](ui/)** | Dark-blue raid HUD mockup with live cooldown rings + DPS meter | …to see the layout / use it as a second-screen reference |

---

## The 10-minute quick start

1. **Read [`docs/00-START-HERE.md`](docs/00-START-HERE.md).** It's short and tells you the order to do things in.
2. **Set up the in-game hotkeys** from [`hotkeys/rogue-socials.txt`](hotkeys/rogue-socials.txt). This alone fixes "too many buttons" — no MQ2 required.
3. **When ready, install MQ2** using [`docs/02-mq2-install-and-setup.md`](docs/02-mq2-install-and-setup.md) and drop in [`macros/RogueBurn.mac`](macros/RogueBurn.mac).
4. **Open [`ui/index.html`](ui/index.html)** in a browser on your ultrawide's second window/monitor to track cooldowns and DPS at a glance.

---

## Design choices (so you know I read your questionnaire)

- **Two keys do 90% of the work.** `RogueBurn` = your single-key burn. `RogueAssist` = the sustained spam-key that keeps you on the kill target. That directly targets your two bottlenecks: *too many buttons* and *DPS inconsistency*.
- **Cooldown tracking is front-and-center.** You asked for it; the HUD shows burn timers as animated rings so you never sit on a ready Rogue's Fury.
- **Corpse recovery, target swapping, burns** — your three most-used actions — each get a dedicated, labeled hotkey.
- **Dark blue + minimal.** The UI theme is exactly that: deep navy, steel accents, low clutter, ultrawide-friendly, scales clean at small–medium.
- **Box-aware.** The Shaman is treated as a support pet: assist + slow/malo/haste handled from the Rogue so you drive everything from one window.

---

## A word on honesty

EverQuest renames and re-ranks abilities every expansion. The macros use the
**real, current ability *line* names** (Rogue's Fury, Frenzied Stabbing,
Twisted Chance, Executioner's Discipline, Ligament Slice, the Spires, etc.), but
**you must slot the highest rank you actually own** and double-check spelling
against your own AA/Combat Ability windows. Every macro has a clearly marked
`CONFIGURE ME` block at the top for exactly this. See
[`docs/04-burn-and-cooldown-reference.md`](docs/04-burn-and-cooldown-reference.md)
for how to confirm names and IDs in-game.

Nothing here is a cheat or a third-party login tool — it's hotkeys, MQ2 macros,
and a local HTML overlay. Use it in line with your server's rules.

**And you don't have to pay for any of it.** MacroQuest is free and open-source
(macroquest.org). RedGuides' paid "Level 2" membership is *optional* and not
required for anything in this package — don't buy it on my account. If you'd
rather spend nothing and skip the install entirely, the in-game hotkeys in
[`hotkeys/`](hotkeys/) give you most of the win for free. See the
"You do NOT have to pay for any of this" section in
[`docs/02-mq2-install-and-setup.md`](docs/02-mq2-install-and-setup.md).
