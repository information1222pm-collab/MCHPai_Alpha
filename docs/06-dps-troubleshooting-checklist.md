# 06 — DPS Inconsistency: The Troubleshooting Checklist

"DPS inconsistency" almost always comes down to a short list of leaks. Run this
checklist when a parse feels low. They're ordered by how often they're the culprit.

## The big three (fix these first — they're ~80% of lost DPS)

- [ ] **Were you behind the mob the whole time?** No backstab from the front =
      half your damage gone. Use `/stick behind` or strafe to the back arc.
- [ ] **Did auto-attack stay ON across target swaps?** Swapping targets silently
      toggles attack off constantly. The [`RogueAssist`](../macros/RogueAssist.mac)
      macro re-asserts `/attack on` every loop — use it.
- [ ] **Did you sit on a ready burn?** A Rogue's Fury or Spire that's up but
      unused is pure lost damage. Watch the [HUD](../ui/index.html) cooldown rings
      and press BURN the instant the window allows.

## Discipline leaks

- [ ] **Empty disc slot.** You should *always* have an offensive disc running.
      The moment one fades, the next should start. Macro handles the hand-off;
      by hand, re-press your disc key when the buff icon drops.
- [ ] **Wasting a big disc on trash.** Save the long-cooldown discs/AAs for
      named/raid targets. On trash, sustained SPAM is enough.
- [ ] **Disc clipping.** Don't overwrite a running offensive disc early unless
      the new one is strictly bigger — you lose the remaining duration.

## Debuff & resist leaks

- [ ] **Ligament Slice (and Shaman Malo) applied early?** Land debuffs in the
      first couple seconds so the *whole* fight benefits, not just the end.
- [ ] **Mob slowed?** Slowed mobs live longer → more of your sustained DPS lands
      and you take less damage. Shaman slow up?

## Gear / setup leaks

- [ ] **Piercing weapon equipped?** Backstab needs it. A slashing/blunt main hand
      kills your spike damage.
- [ ] **Damage augments slotted** in both weapons?
- [ ] **Clicky burn items on a key** and actually fired during burns? (epic-equiv,
      damage clickies.)
- [ ] **Poisons applied?** Modern Rogue poisons are a real DPS line — keep them up.
- [ ] **Haste capped?** Shaman haste + gear should keep you at/near the haste cap.

## Positioning / uptime leaks

- [ ] **Mob mobile / kiting?** Chasing = not swinging. Coordinate with the tank
      to keep it parked; use ranged if it won't sit.
- [ ] **Dying / feigning too much?** Dead Rogues parse zero. Let the Shaman slow
      and keep you topped; don't over-aggro early in a burn — open *after* the
      tank has solid threat.
- [ ] **Standing in AE?** Same as above — survival is DPS over a full fight.

## The 30-second self-audit

After a notable fight, ask:
1. Was I behind it the whole time? (positioning)
2. Did every burn cooldown get used at least once? (the HUD tells you)
3. Was a disc always running? (uptime)
4. Did attack ever drop on a swap? (assist macro prevents this)

If all four are "yes," your parse is as high as your gear allows. Then it's just
gear/AA refinement over time — see
[`07-parsing-and-dps-meter.md`](07-parsing-and-dps-meter.md) to measure progress.
