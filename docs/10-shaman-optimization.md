# 10 — Shaman Optimization (your box's force multiplier)

Your Shaman isn't a side character — set up right, it's the single biggest
boost to your **Rogue's** DPS *and* survival, and it adds a healthy parse of its
own. This is how to make it run itself so you can focus on the Rogue.

> The fastest path: drop **`macros/ShamanAssist.mac`** on the Shaman, set the
> spell names, and bind it. It does everything below automatically. This page
> explains the *why* and the spell set so it's tuned, not generic.

## The Shaman's job, in priority order

A good box Shaman does these every moment, in this order:

1. **Keep the Rogue (and tank) alive** — emergency heals first, always.
2. **Slow the mob** — longer-living mobs hit less *and* let your full sustained
   Rogue DPS actually happen. Slow is survival *and* DPS.
3. **Malo the mob** — lowers its resists so your Rogue's poisons/debuffs and the
   Shaman's own nukes/DoTs land harder.
4. **Maintain buffs** on the Rogue — haste + HP/stat buffs.
5. **Cannibalize** — turn HP into mana so it never goes OOM.
6. **Add DPS** — DoTs + a nuke whenever there's spare mana.

`ShamanAssist.mac` runs exactly this loop: `HEAL > SLOW > MALO > BUFFS > CANNI > DPS`.

## The spell set to keep memmed

You can only cast **memmed** spells, so mem a clean support+DPS set and leave it.
A strong, well-rounded gem layout (slot the highest rank you own of each):

| Gem | Spell type | Example line | Why |
|-----|-----------|--------------|-----|
| 1 | Fast heal | *Chloroblast* line | spam heal for the Rogue/tank |
| 2 | Group heal | *Spiritual/Spirissist* line | when 2+ are hurt |
| 3 | HoT | *Breath of Trushar* line | passive topping between hits |
| 4 | **Slow** | *Turgur's/Tigir's Swarm* line | the big one — keep it landed |
| 5 | **Malo** | *Malosenia/Malosinise* line | resist debuff = more landed damage |
| 6 | Haste buff | *Talisman of the Tribe* / Celerity | Rogue swings = poison procs + auto dmg |
| 7 | DoT #1 | *Curse of …* line | Shaman DPS (big DoTs are excellent) |
| 8 | DoT #2 | *Bite of the …* line | second DoT for layered damage |
| 9 | Nuke | *Spear of …* line | filler DPS / finish |
| 10+| Cure / utility / 2nd buff | situational | counters, rez, etc. |

> Don't have a slot for everything? Heals + Slow + Malo + Haste are the
> non-negotiables. DoTs/nuke are bonus — drop them first if you're tight on gems.

## How the Shaman makes the *Rogue* hit harder (the part people miss)

- **Malo → resists down** → your Rogue's poisons and debuffs (and the Shaman's
  own spells) land more often and for more. Direct Rogue DPS gain.
- **Haste → more swings** → more poison procs and more auto-attack damage. Keep
  the Rogue at/near the **haste cap**.
- **Slow → fights last longer at lower risk** → your Rogue's *sustained* damage
  (most of your parse) actually gets to happen instead of the mob bursting you or
  the tank down early.
- **Heals/Cannib → you stop dying** → a living Rogue parses; a dead one is zero.
  This is most of "less stress."

## The Shaman's own DPS (free parse)

Modern Shaman DoTs hit hard. With `DoDPS` on in `ShamanAssist.mac`, once heals
and debuffs are handled and mana is healthy, the Shaman layers **two DoTs + a
nuke** on the kill target. On a longer fight that's a real second damage column
on top of your Rogue — "competitive parsing" for the *box*, not just the Rogue.

Tuning knobs in the macro:
- `DpsManaMin` (default 55%) — only DPS above this mana, so healing always wins.
- `CanniMana` / `CanniSafeHP` — when it's allowed to cannibalize for mana.
- Turn `DoDPS` off entirely on hard fights where you want pure support.

## Two ways to run it

- **Fully automatic:** `macros/ShamanAssist.mac` on the Shaman (needs MQ2). Set
  names + bind + forget. Pair with `macros/BoxAssist.mac` on the Rogue if you
  want the Rogue to also push targets to the Shaman.
- **Manual (no MQ2):** the one-press hotkeys in
  [`hotkeys/shaman-socials.txt`](../hotkeys/shaman-socials.txt) — SLOW, MALO,
  HEAL, CANNI, BUFF, REZ. Keep the Shaman in a corner of the ultrawide and tab
  over for the few things that matter.

## Personalize it perfectly

Just like the Rogue, run the export trick on the Shaman to confirm exact names:
in game, `/echo ${Me.Book[Turgur's Swarm]}` (prints the gem # if memmed) or open
your spellbook and match spelling. Send those names along with the Rogue's
`RogueExport.ini` and the whole box gets dialed to your exact characters.

## Quick checklist

- [ ] Support set memmed (heals, slow, malo, haste at minimum).
- [ ] `ShamanAssist.mac` names set to your spells + `RogueName`/`TankName`.
- [ ] Slow + Malo landing on every fight.
- [ ] Haste kept on the Rogue (Rogue at haste cap).
- [ ] Cannibalize thresholds set so you never sit at 0 mana.
- [ ] `DoDPS` on for bonus parse when fights allow.
