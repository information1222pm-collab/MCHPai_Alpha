# MCHPai_Alpha — ISBoxer Multibox Command Center

A custom 8-box EverQuest multibox build (Live 130 + TLP 65), built around
**ISBoxer** — no MacroQuest. Single-key burns, instant assist, panic healing,
smart pulls, and class-specific overlays in a clean dark UI.

## Contents

| Path | What it is |
|------|------------|
| `index.html` | The **Command Center** app — a self-contained, offline dashboard: hotbuttons, burn/assist/panic/pull systems, ISBoxer mapped-key recipes, per-class EQ macros, **live buff tracking, proc/named alerts, audio warnings, class-specific overlays**, and a setup guide. Just open it in a browser. |
| `installer/` | The **one-click Windows package**: an HTML navigator (`MCHP-Navigator.hta`) that installs all files, launches every tool, and documents the build — plus the PowerShell installer that backs up the client's ISBoxer config *and* EverQuest UI before laying everything down. See `installer/README.md`. |

## Quick start (client)

1. Unzip the package and double-click **`installer/Launch-Navigator.bat`**.
2. Click **Install** in the navigator (or run `installer/Install.bat` directly).
3. From the navigator: open the Command Center, build ISBoxer from the recipe,
   paste the EQ socials, and play. Don't like it? Use **Restore my old EQ UI**.

100% native ISBoxer. Prepared by MCHP Boxing Services.
