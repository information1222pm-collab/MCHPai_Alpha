# 05 — Shaman Box Coordination (drive everything from the Rogue)

You box a **Rogue (main driver) + Shaman**. The goal: you play the Rogue, and the
Shaman quietly does its job — slow, debuff, heal, haste, rez — without you
alt-tabbing constantly.

## Why the Shaman makes your Rogue hit harder

- **Malo / Malosenia line** — lowers the mob's resists and (with the right line)
  helps your poisons/debuffs land. More of your damage sticks.
- **Slow** — keeps you and the tank alive, which means **longer fights = more of
  your sustained DPS actually happening** instead of dying/feigning.
- **Haste / Talisman of Celerity + group buffs** — straight melee throughput for
  the Rogue.
- **Cannibalize** — Shaman turns HP into mana so it never goes OOM mid-fight.
- **Roar / DoTs** — bonus raid/group damage while it's not busy healing.

## Two ways to coordinate

### A. No MQ2 (manual, works on any server)
Make a few key Shaman actions into **single hotkeys on the Shaman's hotbar**, and
keep the Shaman window in a corner of your ultrawide. You tab over only for the
occasional slow/malo/rez. Use [`hotkeys/shaman-socials.txt`](../hotkeys/shaman-socials.txt).

### B. With MQ2 + a comms plugin (recommended for hands-off)
Install **MQ2DanNet** (or **MQ2EQBC**) on both characters. Now the Rogue can send
commands to the Shaman over the network. [`macros/BoxAssist.mac`](../macros/BoxAssist.mac)
shows the pattern. Core idea:

```
// from the Rogue, tell the Shaman to assist & debuff the Rogue's target:
/dgt /target id ${Target.ID}
/dgt /casting "Malosenia Rk. II"
/dgt /casting "Turgur's Swarm"          // slow — use your highest rank
```

(`/dgt` = DanNet "tell group/all"; with EQBC it's `/bct <name> //...`.)

## A clean division of labor

| You press (on the Rogue) | Shaman does (via macro/network) |
|---------------------------|----------------------------------|
| **BURN** | (Shaman keeps healing/cannib; optionally drops a DoT) |
| **ASSIST/SPAM** | Shaman targets your target, slows + malos if not already |
| **PULL** (if you pull) | Shaman holds, then slows on engage |
| **REZ** hotkey | Shaman targets corpse and casts rez |
| **CORPSE** (your own deaths) | — handled on the Rogue, see socials |

## Suggested Shaman "set it and forget it" loop

For true hands-off, run a simple heal/buff loop on the Shaman (Very Vanilla MQ
ships class routines, or use a community Shaman heal macro). Keep it to:

1. **Heal** the Rogue (and tank in groups) below a threshold.
2. **Slow + Malo** the assist target if missing.
3. **Cannibalize** when mana is low and HP is safe.
4. **Keep buffs/haste up** on the Rogue.

That frees you to do nothing but Rogue: position, SPAM, BURN.

## Rez & recovery (you flagged corpse recovery as a top action)

- Give the **Shaman a one-press rez hotkey** targeting your corpse. After a
  wipe, you summon corpses / run back, target your corpse, and the Shaman rezzes.
- See the **CORPSE** section in [`hotkeys/rogue-socials.txt`](../hotkeys/rogue-socials.txt)
  for the `/corpse`, `/consent`, and find-corpse helpers.

Next: tighten your numbers in
[`06-dps-troubleshooting-checklist.md`](06-dps-troubleshooting-checklist.md).
