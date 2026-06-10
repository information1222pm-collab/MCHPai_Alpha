# UI — Rogue DPS HUD (dark blue, raid-oriented)

`index.html` is a **self-contained** HUD you can open by double-clicking it (no
install, no server, works offline). It's styled exactly to your brief: deep navy
+ steel, minimalist, ultrawide 3-column layout, small–medium scale, with a cold
"rogue" accent.

## What it shows

- **Burn Cooldowns** — animated rings that count down. When an ability is ready,
  its ring lights up cyan and pulses so you never sit on a Rogue's Fury or Spire.
- **DPS Meter** — your live DPS number, a group/raid bar comparison, and a
  breakdown of your damage by source (Backstab, Assassinate, poisons, etc.).
- **Target panel** — HP, and whether the mob is Slowed / Malo'd / debuffed.
- **Box & State** — auto-attack on, disc running, Shaman assisting, behind-target.

## Using it

1. Double-click `index.html` (or drag into any browser).
2. Park it in a window on the side of your **ultrawide**, or on a second monitor.
3. Press **▶ BURN** / **⇄ Swap Target** to see the demo react.

## Make it match your character

Open `index.html` in a text editor. Near the top of the `<script>` you'll find:

- `COOLDOWNS` — edit each ability **name** and **cd** (cooldown in seconds) to
  match what you own. (See `../docs/04-burn-and-cooldown-reference.md`.)
- `ROSTER` — your group/raid names for the meter.
- `SOURCES` — your damage-source labels for the breakdown.

## Going live (optional)

Out of the box the numbers are **simulated** for layout — it's a design +
glanceable-cooldown tool. To drive the DPS meter from real data, find the
`// LIVE DATA HOOK` comment in the script and feed it parsed numbers from
GamParse or an MQ2 parse plugin (shape: `{ who, me, dps }`). See
`../docs/07-parsing-and-dps-meter.md`.
