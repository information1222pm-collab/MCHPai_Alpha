# 03 — Rogue DPS Rotation & Positioning

This is the heart of it. Learn this and you're 90% of the way to consistent,
competitive parses.

## The golden rule: be behind the mob

- **Backstab requires a piercing weapon and you behind the target.** It's your
  single biggest melee hit and the trigger for **Assassinate** procs.
- If you're in front or to the side, you're throwing away most of your damage.
- Boxed/solo: use MQ2 `/stick behind` (or `/stick 10 behind`) so you auto-park
  behind the mob. In a raid where the tank rotates the mob, **strafe to stay on
  its back arc**. This is the #1 cause of "DPS inconsistency."

## Sustained rotation (what's always happening)

This is the boring, constant part — and it's most of your damage:

1. **Auto-attack ON** the kill target.
2. **Backstab on cooldown** (it's fast; spam the key or let the macro do it).
3. Keep an **offensive discipline** running at all times (replace it when it
   fades — never let the slot sit empty).
4. Apply your **debuff** (Ligament Slice line) once at the start of a fight.
5. Throw (ranged disc) **only** when you physically can't be behind the mob.

The [`RogueAssist`](../macros/RogueAssist.mac) macro does all five for you on a
loop. Without MQ2, the [`hotkeys/rogue-socials.txt`](../hotkeys/rogue-socials.txt)
"SPAM" key covers Backstab + attack + assist.

## Burn rotation (the spike)

A "burn" is when you dump every cooldown for a damage window (named mobs, raid
bosses, "burn it down" moments). **Order matters** — lead with the long buffs so
everything else benefits from them.

**Recommended burn order** (fire top-to-bottom; the macro does this in a fraction of a second):

1. **Third Spire of the Rake** — long crit buff; lead with it.
2. **Rogue's Fury** — your signature accuracy/crit/min-damage buff. Always part of a burn.
3. **Offensive discipline** — your highest-rank big disc (Frenzied Stabbing line / SoR equivalent). *Only one disc at a time*, so pick the biggest.
4. **Twisted Chance / Bestow Twisted Chance** — opens the synergy amp window.
5. **Ligament Slice** — damage-add / debuff (also your opener on non-burn fights).
6. **The rest of your activated AAs** — Frenzied Stabbing (AA), Twisted Shank, Banestrike, Envenomed Blades, Focused Rampage, Absorbing Agent, etc. — fire whatever is ready.
7. **Clicky burn items** — epic-equivalent, damage clickies, illusion/aug clickies that boost melee.
8. Keep **Backstab + auto-attack** hammering the whole time.

> When the first disc fades mid-burn, immediately follow with your next disc
> (Executioner's → Knifeplay → Razor's Edge → Arcworker lines, highest rank
> first). The macro handles the hand-off; by hand, just re-press your disc key
> when the buff drops.

**You do not need to memorize this.** Press the
[`RogueBurn`](../macros/RogueBurn.mac) key (or the BURN hotkey) and it fires the
whole stack in order. The list above is just so you understand what's happening
and can tune the priority.

## Putting it together on a real fight

**Trash pull / group mob:**
- Assist → behind the mob → SPAM key (sustained). Burn only if it's a tough named.

**Named / raid boss:**
1. Get behind it, Ligament Slice (debuff) lands.
2. Hit **BURN** at the pull (or on the raid's burn call).
3. Run the **SPAM/assist** key continuously the whole fight.
4. Re-press **BURN** every time it's back up (track it on the
   [HUD](../ui/index.html) so you never miss a window).

**Can't get behind it (frontal cleave / wall hugger):**
- Switch to **ranged**: equip throwing, run your throwing/Fatal-Aim disc, keep
  burning. Less than backstab damage, but far better than eating cleaves.

## Target swapping (one of your top-3 actions)

- Bind a **"swap to MA's target"** key (assist). On a swap, **attack can toggle
  off** — that's a classic hidden DPS leak. The [`RogueAssist`](../macros/RogueAssist.mac)
  macro re-asserts `/attack on` after every swap so you never silently stop hitting.
- Without MQ2: the in-game "ASSIST + ATTACK" social hotkey does the same in two
  lines.

Next: [`04-burn-and-cooldown-reference.md`](04-burn-and-cooldown-reference.md)
to map these names to *your* abilities and confirm cooldowns.
