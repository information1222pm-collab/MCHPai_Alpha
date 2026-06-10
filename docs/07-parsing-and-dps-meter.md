# 07 — Parsing & DPS Meter (measure to get competitive)

You wanted **DPS meters** and **competitive parsing**. You can't tune what you
can't see. Here's how to measure, and how the included HUD fits in.

## Option 1 — GamParse / external log parser (gold standard)

EQ writes a combat log you can parse:

1. In game, enable logging: `/log on` (toggle), and turn on combat damage in
   Options so hits/crits are written to the log.
2. Point an external parser at
   `...\EverQuest\Logs\eqlog_<Char>_<server>.txt`.
3. **GamParse** is the long-standing community DPS parser — per-fight DPS, crit
   rates, ability breakdowns, and the ability to compare attempts.
4. Parse the **same target type** repeatedly (e.g. a raid boss or a known named)
   so your numbers are comparable run to run.

What to look at:
- **Total DPS** and **damage %** vs. the rest of the group/raid (relative is more
  honest than absolute).
- **Backstab + Assassinate share** — should be a big chunk. Low = positioning
  problem (see [checklist](06-dps-troubleshooting-checklist.md)).
- **Burn uptime** — did your big hits land once per fight per cooldown?

## Option 2 — In-game / MQ2 parse

If you're running MQ2, community DPS/parse plugins (e.g. an MQ damage parser)
give a live in-game readout without alt-tabbing. Lighter than GamParse but great
for quick "is this rotation better?" checks at a dummy.

## Option 3 — The included HUD (`ui/index.html`)

The [HUD in this package](../ui/index.html) is a **cooldown tracker + DPS-meter
visual** styled to your spec (dark blue, minimalist, ultrawide-friendly). Out of
the box it runs as a **standalone visual reference / demo**:

- **Cooldown rings** animate down so you can *see* when Rogue's Fury, Spire,
  Twisted Chance, etc. are coming back up — the direct fix for "sitting on
  cooldowns."
- The **DPS meter panel** shows a rolling damage readout and a bar comparison.

> Out of the box the HUD's numbers are **simulated** for layout/demo purposes —
> it's a design + at-a-glance cooldown tool, not yet wired to your live log. To
> make the DPS meter *live*, feed it your parser's output (GamParse can export,
> or an MQ2 plugin can write a small JSON the HUD reads). The HTML is commented
> where the live data hook goes (`// LIVE DATA HOOK`). Keep GamParse as the
> source of truth for serious parsing; use the HUD for glanceable cooldowns.

Open it by double-clicking `ui/index.html`, or drag it into any browser. Park it
in a window on the side of your ultrawide.

## A simple tuning loop

1. Parse a baseline fight with GamParse. Save the number.
2. Change **one** thing (fix positioning, add a clicky to the burn, re-order a
   disc).
3. Parse the same fight again.
4. Keep the change if DPS went up; revert if not.
5. Repeat. This is how you go from "decent" to "competitive" without guessing.

That's the whole science of it. Position, use your cooldowns, measure, refine.
