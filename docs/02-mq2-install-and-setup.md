# 02 — MQ2 Install & Setup (for someone who's never used it)

MQ2 (MacroQuest) is the tool that lets one keypress run a whole sequence. You
said you're "going to learn MQ2" — this is the gentle on-ramp. We only use the
parts you actually need for DPS.

> **Rules first.** MacroQuest is allowed on emulator servers that permit it and
> is **against the rules on the official live servers (DBG)**. Know which server
> you're on. The **in-game hotkeys** in [`hotkeys/`](../hotkeys/) work everywhere
> and require no MQ2 — if you're on live, use those and skip the macros. The rest
> of this file assumes you're on a server where MQ2 is permitted.

## What MQ2 actually is

Think of it as a scripting layer on top of EQ. For us it does three things:

1. **TLOs (Top-Level Objects)** — read game state, e.g. `${Me.AltAbilityReady[Rogue's Fury]}`
   tells you if an ability is off cooldown.
2. **Commands** — do things, e.g. `/alt activate 1234`, `/disc Frenzied Stabbing`,
   `/attack on`.
3. **Macros (`.mac` files)** — saved sequences you run with `/mac name`.

## You do NOT have to pay for any of this

Let's be clear up front, because this trips people up:

- **MacroQuest is free and open-source.** The core project lives at
  **macroquest.org** (source on GitHub) and costs nothing. Everything in this
  package — all three macros — runs on the **free** MacroQuest.
- You may have seen **RedGuides** mentioned around the community. RedGuides
  packages a convenient one-click build ("Very Vanilla") and hosts some
  *premium* plugins/scripts behind a paid "Level 2" membership. **That paid tier
  is optional and not required for anything here.** Don't buy it unless you
  later decide you want a specific paywalled convenience script.
- **The cheapest path of all is zero MQ2:** the in-game social hotkeys in
  [`hotkeys/`](../hotkeys/) give you a clean 2-key-ish setup that costs nothing,
  needs no install, and works on every server. If money or hassle is a concern,
  start (and honestly, you can stay) there.

## Install (one time, free)

Pick whichever is easiest for you — both are free:

- **Free MacroQuest (macroquest.org / GitHub)** — the official open-source build.
  Compile it or grab a free pre-built for your server. No account, no payment.
- **Server-provided MQ build** — many emulator servers ship their own free build.
  If your server has one, use *that* one (best compatibility), and it's free too.
- **RedGuides "Very Vanilla"** — *optional* convenience installer. A free
  RedGuides account covers the basics; you only ever pay if you specifically want
  their premium scripts, which this package does not need.

General steps (your distribution's installer will mostly do this for you):

1. Add an **antivirus exclusion** for the MQ folder (it's not malware, but AV
   flags injectors). Only do this if you trust your source.
2. Run the **launcher**, then start EverQuest from it (or inject after EQ is up).
3. In game, hit the MQ console hotkey (often the back-tick `` ` ``) or type
   `/mqconsole` depending on build, and confirm `/echo Hello` prints back.

## Drop in the macros

1. Find your MQ **`Macros`** folder (e.g. `...\MacroQuest\Macros\`).
2. Copy these files from this package into it:
   - [`macros/RogueBurn.mac`](../macros/RogueBurn.mac)
   - [`macros/RogueAssist.mac`](../macros/RogueAssist.mac)
   - [`macros/BoxAssist.mac`](../macros/BoxAssist.mac)
3. **Open each one and edit the `CONFIGURE ME` block at the top** so the ability
   names match what *you* own. (Walkthrough in
   [`04-burn-and-cooldown-reference.md`](04-burn-and-cooldown-reference.md).)

## Run them

In game:

```
/mac RogueBurn          // fires your full burn once, then ends
/mac RogueAssist        // sustained: assist main, attack, keep backstab up
/endmacro               // stop whichever macro is running
```

You won't type these every time — you'll bind them to keys. Make in-game social
hotkeys whose only line is the `/mac` command, or use MQ2's `/bind`:

```
/bind LeftAlt+1 /mac RogueBurn
/bind LeftAlt+2 /mac RogueAssist
/bind LeftAlt+0 /endmacro
```

## Plugins worth having (optional, DPS-relevant)

- **MQ2DanNet** or **MQ2EQBC** — lets your Rogue send commands to the Shaman
  (used by [`BoxAssist.mac`](../macros/BoxAssist.mac) and
  [`05-shaman-box-coordination.md`](05-shaman-box-coordination.md)).
- **MQ2Cast** — cleaner spell/disc casting with success/fail detection.
- A **parser/DPS plugin** or external parser — see
  [`07-parsing-and-dps-meter.md`](07-parsing-and-dps-meter.md).

## If something doesn't work

- `/echo ${Me.AltAbility[Rogue's Fury].ID}` prints a number → the name is right.
  Prints `NULL` → the name is wrong/spelled differently; fix it in the macro.
- Macro errors print a line number — open the `.mac`, go to that line.
- Disc won't fire? You're probably already running another disc (only one
  offensive disc at a time) or it's on cooldown — both are normal.

Next: [`03-rogue-dps-rotation-and-positioning.md`](03-rogue-dps-rotation-and-positioning.md)
