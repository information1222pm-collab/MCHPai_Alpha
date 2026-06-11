# MCHP Boxing — ISBoxer Command Center Package

A one-click Windows package that sets up the whole multibox build for the
client, so they don't configure anything by hand. Everything is driven from a
single HTML navigator.

## What's in this folder

| File | Purpose |
|------|---------|
| `Launch-Navigator.bat` | **Double-click this first.** Opens the package navigator. |
| `MCHP-Navigator.hta` | The HTML navigator — installs files, launches every tool, and documents the build. Runs as a Windows HTML Application (local privileges). |
| `Install.bat` | Runs the installer directly (the navigator's Install button calls this). |
| `Install-MCHP-Boxing.ps1` | The installer itself (PowerShell). |
| `CommandCenter.html` | The visual command-center app (gets installed + a desktop shortcut). |

Hand the client the whole `installer` folder (zip it). They double-click
**`Launch-Navigator.bat`**, then click **Install** — or, if they prefer, run
`Install.bat` directly.

## The navigator (front door)

`MCHP-Navigator.hta` is a single-window hub with tabs: **Overview · Install ·
Launch Tools · Documentation · Backups & Restore · About**. From it the client can:

- **Install / re-run setup** (calls `Install.bat`)
- **Open the Command Center**, ISBoxer build recipe, EQ macros, audio triggers, inventory layout
- **Launch ISBoxer / Inner Space** and (optionally) EverQuest
- **Restore their old EQ UI** with one click
- Read documentation for every feature

It's an `.hta` (not a plain `.html`) on purpose: only an HTML Application can
touch the filesystem and launch programs. It's written IE/MSHTML-safe (the engine
mshta uses) so it runs on any Windows 10/11 machine with no dependencies.

## What the installer does — automatically

1. Creates a clean `Documents\MCHP-Boxing\` install folder.
2. **Backs up** the client's existing `ISBoxer Toolkit.xml` (never overwrites it).
3. **Backs up the client's EverQuest UI files** — every `*_<server>.ini` layout/
   config file plus the whole `uifiles\` custom-skin folder — into a timestamped
   `Backups\EQ-UI-*` folder, and drops a **one-click `Restore-EQ-UI.bat`** in there
   so he can roll back to his old UI any time he doesn't like the new one.
   (EQ is auto-detected; if not found the installer asks for the path or you can
   pass `-EQDir "C:\path\to\EverQuest"`. Skip with `-SkipUIBackup`.)
4. Writes **ready-to-paste EQ socials** — one `.txt` per character, both teams
   (`EQ-Macros\Live` and `EQ-Macros\TLP`).
5. Writes the **ISBoxer build recipe** (ATGs, mapped keys, steps) to
   `ISBoxer-Profiles\`.
6. Writes the **EQ audio-trigger** list and **inventory layout**.
7. Installs the **Command Center app** and a **Desktop shortcut**.
8. Opens the `00-START-HERE.txt` guide and the install folder when done.

### Rolling back the UI

Open the newest `Documents\MCHP-Boxing\Backups\EQ-UI-*` folder, close EverQuest,
and double-click **`Restore-EQ-UI.bat`**. It copies his original `.ini` layout
files and `uifiles\` skins back over the EQ install. Nothing is destructive —
the new build mostly *adds* socials/hotbuttons, and his originals are preserved.

Uninstall: `powershell -ExecutionPolicy Bypass -File Install-MCHP-Boxing.ps1 -Uninstall`

## The one honest limitation

EverQuest stores in-game **socials and hotbuttons on Daybreak's servers**, per
character — so **no installer (this one or any other) can silently write them**.
The installer pre-builds every social as a `.txt` file, turning what would be an
hour of typing into a quick copy-paste pass (once per box). Everything else —
folders, backups, ISBoxer profile import, audio triggers, the app, the shortcut —
is automated.

The ISBoxer profile is delivered as an exact **build recipe** rather than a raw
`ISBoxer Toolkit.xml` overwrite, because that file is tied to the client's own
game install, window names, and account slots. The recipe takes ~10 minutes and
is guaranteed correct for their machine; their old config is safely backed up
first so they can experiment freely.

## Requirements

Windows (EverQuest + Inner Space/ISBoxer are Windows-only). PowerShell 5.1
(built into Windows 10/11) or newer. No admin rights needed — everything installs
under the user's Documents.
