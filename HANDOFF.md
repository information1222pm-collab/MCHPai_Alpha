# Your Rogue DPS Setup — Delivery & Quick Start

Hey Cloudi — here's your complete Rogue DPS package. It's built specifically for
your situation: a returning player (Omens → Shattering of Ro), Rogue + Shaman
2-box, aiming at endgame grouping and raiding, on an ultrawide, dark-blue and
minimalist. The whole point is to get you doing **maximum DPS with 2 keys**, so
you can stop worrying about "where do I even begin" and just play.

## What you got

**A. A click-through setup wizard — start here**
Open **`setup.html`** in any browser. Type your character names once and it
auto-fills every macro and hotkey for you, with copy/download buttons. No file
editing, no folder hunting, no prior MQ2 knowledge needed.

**B. Two ways to play — both free**
- **In-game hotkeys** (`hotkeys/`) — works on *any* server including live, zero
  install. A clean ASSIST / SPAM / BURN bar that fixes "too many buttons" today.
- **MacroQuest macros** (`macros/`) — for emu servers, turns your whole burn into
  one key. Uses the **free, open-source** MacroQuest (you never pay anyone).

**C. A medieval dark-blue raid HUD** (`ui/index.html`)
- Animated **cooldown rings** so you never sit on a ready Rogue's Fury or Spire.
- A **real DPS meter**: drag in your `eqlog.txt` and it shows your actual DPS,
  crit rate, per-ability breakdown, and your Backstab/Assassinate share (with a
  flag if your positioning is costing you damage).

**C2. A before/after DPS comparison** (`ui/compare.html`)
- Shows what each fix is worth (positioning, burns, poisons, gear, haste…) and
  the total projected uplift. Then **prove it**: drop in an old log and a new log
  and it measures your real before → after change.

**C3. A fully optimized Shaman** (`macros/ShamanAssist.mac` + `docs/10`)
- Drop it on the Shaman and it runs itself: emergency heals → slow → malo →
  haste/buffs → cannibalize → bonus DoT/nuke DPS. Keeps you alive and hitting
  harder, and adds a second damage column to the box's parse.

**D. A printable cheat card** (`ui/cheatsheet.html`)
One page, the whole rotation + permanent-gains checklist. Print it, keep it by
the keyboard.

**E. Plain-English guides** (`docs/`)
Returning-player catch-up, the rotation & positioning, the burn order, Shaman
coordination, a "why is my DPS low" checklist, gear/poison/weapon fixes, and
parsing.

## Get going in ~10 minutes

1. Open **`setup.html`**, type your Rogue / Shaman / Tank names at the top.
2. Pick a path (the wizard recommends in-game hotkeys to start).
3. Follow the steps — copy/download as you go.
4. Open **`ui/index.html`** on the side of your ultrawide.
5. In game: **SPAM** at the pull, **BURN** on named/bosses, stay **behind** the mob.

That alone will already feel like a different character.

## One thing from you → a perfectly-tuned setup (2 minutes)

Every Rogue owns slightly different AAs at different ranks, so the macros ship
with the *common current names* as sensible defaults. To make them **exactly**
match your character (correct names + activation IDs, nothing guessed):

1. Once you have MacroQuest running, run: **`/mac ExportAbilities`**
2. It prints your owned burn abilities + every discipline you know, and writes a
   file: `…\MacroQuest\config\RogueExport.ini`
3. **Send me that file** (or a screenshot of the printout).

I'll plug your exact abilities into your macros and the HUD's cooldown timers so
it's 100% dialed to *your* Rogue. Until then, anything that doesn't match your
character is simply skipped — so it all still works, it's just not yet perfectly
tuned.

## What this is (and isn't)

Hotkeys, MQ2 macros, and a local HTML overlay — no cheats, no login tools,
nothing that costs money. Use MacroQuest only where your server allows it (it's
against the rules on official live servers; the in-game hotkey path works there
instead).

Anything you want tweaked — colors, key layout, which abilities are in the burn,
the Shaman's role — just say the word and I'll adjust it.

— Enjoy wrecking things again. 🗡️
