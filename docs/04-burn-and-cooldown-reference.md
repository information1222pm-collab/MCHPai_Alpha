# 04 — Burn & Cooldown Reference (map names to *your* abilities)

The macros and HUD ship with the **real ability line names**, but EQ re-ranks and
occasionally renames things every expansion. This page shows you how to confirm
exactly what you own and plug it into the `CONFIGURE ME` blocks.

## How to find an ability's real name & ID in-game

With MQ2 loaded, type these in the chat console:

```
/echo ${Me.AltAbility[Rogue's Fury].ID}        // AA: prints a number if you own it, NULL if name is off
/echo ${Me.AltAbilityReady[Rogue's Fury]}      // TRUE/FALSE = is it off cooldown
/echo ${Me.CombatAbility[1]}                    // prints the disc in your 1st Combat Ability slot
/alt list                                       // dumps all your AAs with IDs (a lot — scroll)
```

Without MQ2: open the **Alternate Advancement** window and the **Combat Abilities**
window and read the names directly. Spelling/punctuation must match exactly
(including the apostrophe in `Rogue's`).

> **Tip:** If an `${Me.AltAbility[Name].ID}` returns NULL, the name string is
> wrong. Try the AA window's exact text, or use the numeric ID instead:
> `/alt activate 1234`.

## The Rogue burn toolkit (current lines)

Slot the **highest rank you own**. Names below are the *lines* — in SoR they may
read as a newer tier, but the function is identical.

### Discs (only ONE offensive disc runs at a time — pick the biggest)
| Line | Role | Notes |
|------|------|-------|
| **Frenzied Stabbing Discipline** | Big sustained offensive disc | Common burn lead disc |
| **Executioner's Discipline** | Offensive disc | Use as the next disc when one fades |
| **Knifeplay Discipline** | Offensive disc | Disc hand-off chain |
| **Razor's Edge Discipline** | Offensive / frontal | Good when you can't stay perfectly behind |
| **Arcworker Discipline** | Offensive disc | Later disc in the hand-off chain |
| **Fatal Aim / ranged disc line** | Throwing burn | For fights you can't get behind |

### Activated AAs (these STACK — fire them all during a burn)
| AA | Role |
|----|------|
| **Rogue's Fury** | Core: accuracy + crit + min-damage. Always in a burn. |
| **Third Spire of the Rake** | Crit damage/chance buff. Lead the burn with it. |
| **Twisted Chance / Bestow Twisted Chance** | Opens the melee synergy amp window. |
| **Frenzied Stabbing** (AA version) | Extra attacks. |
| **Ligament Slice** | Damage-add + debuff. Also your fight opener. |
| **Twisted Shank** | Burst attack AA. |
| **Banestrike** | Bane-damage strike. |
| **Envenomed Blades** | Poison proc buff (self). |
| **Focused Rampage / Intensity of the Resolute** | General melee burn amps (shared melee AAs). |
| **Absorbing Agent** | Damage/utility proc. |

> Don't have one of these yet, or it's named differently in SoR? Just delete or
> rename that line in the macro's `CONFIGURE ME` block. The macro skips anything
> it can't find, so a wrong name = that one ability is silently ignored, nothing
> breaks.

## Approximate cooldowns (for the HUD)

These drive the cooldown rings in [`ui/index.html`](../ui/index.html). They're
**ballpark** — confirm against your own timers and edit the `COOLDOWNS` object at
the top of the HTML file. Reuse timers shift with AA rank and gear.

| Ability | Rough reuse |
|---------|-------------|
| Rogue's Fury | ~3 min (much less with Focused/Glyph) |
| Third Spire of the Rake | ~7.5 min |
| Twisted Chance | ~1 min |
| Frenzied Stabbing (AA) | ~3–4 min |
| Ligament Slice | ~12–24 sec (debuff refresh) |
| Twisted Shank | ~1.5 min |
| Big offensive disc | ~varies (disc timer group) |
| Throwing burn disc | ~varies |

## The single source of truth

When you set the names once, set them in **all four** places so everything agrees:

1. [`macros/RogueBurn.mac`](../macros/RogueBurn.mac) — `CONFIGURE ME` block
2. [`macros/RogueAssist.mac`](../macros/RogueAssist.mac) — `CONFIGURE ME` block
3. [`hotkeys/rogue-socials.txt`](../hotkeys/rogue-socials.txt) — the named lines
4. [`ui/index.html`](../ui/index.html) — the `COOLDOWNS` array

Set them once, and the whole package speaks the same language as your character.
