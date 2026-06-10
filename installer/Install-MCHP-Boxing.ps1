<#
======================================================================
  MCHP Boxing Services
  ISBoxer Multibox Command Center - Installer
----------------------------------------------------------------------
  What this does (fully automatic):
    * Creates a clean install folder in your Documents
    * Backs up your existing ISBoxer Toolkit config (never overwrites it)
    * Lays down every EQ social/macro as ready-to-paste .txt files
    * Drops in the ISBoxer build recipe + EQ audio-trigger list
    * Installs the Command Center app + a Desktop shortcut
    * Opens the Start-Here guide when finished

  Honest note: EverQuest stores in-game socials/hotbuttons on Daybreak's
  servers per character, so they cannot be silently file-installed by ANY
  tool. This installer pre-builds them so adding them in-game is a quick
  copy-paste instead of an hour of typing. Everything else is automated.

  Usage:
    Double-click Install.bat   (recommended)
    -or-  right-click this file > Run with PowerShell
    Uninstall:  powershell -ExecutionPolicy Bypass -File Install-MCHP-Boxing.ps1 -Uninstall
======================================================================
#>

param(
  [switch]$Uninstall,
  [string]$InstallRoot
)

$ErrorActionPreference = 'Stop'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition

# ---------- pretty output helpers ----------
function Line($c='-')      { Write-Host ('  ' + ($c * 64)) -ForegroundColor DarkCyan }
function Head($t)          { Write-Host ''; Write-Host "  $t" -ForegroundColor Cyan; Line }
function Ok($t)           { Write-Host "   [OK]   $t" -ForegroundColor Green }
function Info($t)         { Write-Host "   [..]   $t" -ForegroundColor Gray }
function Warn($t)         { Write-Host "   [!]    $t" -ForegroundColor Yellow }
function Step($t)         { Write-Host "   ->     $t" -ForegroundColor White }

function Banner {
  Clear-Host
  Write-Host ''
  Write-Host '   __  __  ___ _  _ ___   ' -ForegroundColor Cyan
  Write-Host '  |  \/  |/ __| || | _ \   B O X   O P S' -ForegroundColor Cyan
  Write-Host '  | |\/| | (__| __ |  _/   ISBoxer Multibox Command Center' -ForegroundColor Cyan
  Write-Host '  |_|  |_|\___|_||_|_|     Installer  v1.0' -ForegroundColor DarkCyan
  Write-Host ''
  Write-Host '  MCHP Boxing Services - custom 8-box build (Live 130 + TLP 65)' -ForegroundColor Gray
  Write-Host '  Native ISBoxer. No MacroQuest.' -ForegroundColor DarkGray
  Write-Host ''
}

# ---------- resolve paths ----------
$Docs = [Environment]::GetFolderPath('MyDocuments')
$Desktop = [Environment]::GetFolderPath('Desktop')
if (-not $InstallRoot) { $InstallRoot = Join-Path $Docs 'MCHP-Boxing' }
$IsboxerCfgDir = Join-Path $Docs 'Inner Space\Configuration'
$IsboxerXml    = Join-Path $IsboxerCfgDir 'ISBoxer Toolkit.xml'

# =====================================================================
#  UNINSTALL
# =====================================================================
if ($Uninstall) {
  Banner
  Head 'Uninstall'
  if (Test-Path $InstallRoot) {
    Warn "This will remove: $InstallRoot"
    Info 'Your ISBoxer config and its backups are NOT touched.'
    $ans = Read-Host '   Type YES to confirm'
    if ($ans -eq 'YES') {
      Remove-Item $InstallRoot -Recurse -Force
      $lnk = Join-Path $Desktop 'MCHP Command Center.lnk'
      if (Test-Path $lnk) { Remove-Item $lnk -Force }
      Ok 'Removed install folder and desktop shortcut.'
    } else { Info 'Cancelled.' }
  } else { Info 'Nothing installed at that location.' }
  Write-Host ''
  return
}

# =====================================================================
#  TEAM DATA  (mirrors the Command Center app exactly)
#  Each character -> the EQ social buttons they run.
# =====================================================================
$Teams = @(
  @{ Team='Live'; Lvl=130; Chars=@(
    @{ Slot=1; Name='Brunnar'; Class='Warrior'; Win='W1'; Role='Main Tank / Main Assist (driver)'
       Socials=@(
         @{ Btn='Assist'; Key='~';  Lines=@('/target Brunnar','/xtarget 1 set') }
         @{ Btn='Burn';   Key='F1'; Lines=@('/disc Brace for Death','/alt activate 3699','/disc Forceful Rebuke') }
         @{ Btn='Panic';  Key='F2'; Lines=@('/disc Brace for Death','/alt activate 511','/alt activate 1242') }
       )}
    @{ Slot=2; Name='Aelith'; Class='Cleric'; Win='W2'; Role='Primary healer (tank chain)'
       Socials=@(
         @{ Btn='Assist'; Key='~';  Lines=@('/target Brunnar','/xtarget 1 set') }
         @{ Btn='Burn';   Key='F1'; Lines=@('/cast 7','/cast 1') }
         @{ Btn='Panic';  Key='F2'; Lines=@('/cast 8','/alt activate 416','/cast 2') }
       )}
    @{ Slot=3; Name='Sylwen'; Class='Druid'; Win='W3'; Role='Secondary healer / DPS filler'
       Socials=@(
         @{ Btn='Assist'; Key='~';  Lines=@('/target Brunnar','/xtarget 1 set') }
         @{ Btn='Burn';   Key='F1'; Lines=@('/alt activate 1468','/alt activate 538','/cast 12','/cast 11') }
         @{ Btn='Panic';  Key='F2'; Lines=@('/cast 8','/cast 1','/alt activate 825') }
       )}
    @{ Slot=4; Name='Quillan'; Class='Bard'; Win='W4'; Role='DPS / haste / mez / backup puller'
       Socials=@(
         @{ Btn='Assist'; Key='~';  Lines=@('/assist Brunnar','/attack on','/melody 1 2 3') }
         @{ Btn='Burn';   Key='F1'; Lines=@('/alt activate 482','/alt activate 3704','/cast 1','/melody 1 2 3') }
         @{ Btn='Panic';  Key='F2'; Lines=@('/twist stop','/cast 6','/melody 1 2 6') }
         @{ Btn='Pull';   Key='G';  Lines=@('/stand','/cast 7','/alt activate 209') }
       )}
    @{ Slot=5; Name='Grokk'; Class='Beastlord'; Win='W5'; Role='Pet + melee DPS / slow'
       Socials=@(
         @{ Btn='Assist'; Key='~';  Lines=@('/assist Brunnar','/attack on','/pet attack') }
         @{ Btn='Burn';   Key='F1'; Lines=@('/alt activate 1391','/alt activate 2982','/disc Frenzied Swipes','/alt activate 1387') }
         @{ Btn='Panic';  Key='F2'; Lines=@('/alt activate 1389','/cast 6') }
       )}
    @{ Slot=6; Name='Thokk'; Class='Beastlord'; Win='W6'; Role='Pet + melee DPS / backup slow'
       Socials=@(
         @{ Btn='Assist'; Key='~';  Lines=@('/assist Brunnar','/attack on','/pet attack') }
         @{ Btn='Burn';   Key='F1'; Lines=@('/alt activate 1391','/alt activate 2982','/disc Frenzied Swipes','/alt activate 1387') }
         @{ Btn='Panic';  Key='F2'; Lines=@('/alt activate 1389','/cast 6') }
       )}
    @{ Slot=7; Name='Tsuro'; Class='Monk'; Win='W7'; Role='Melee DPS / PRIMARY PULLER (FD split)'
       Socials=@(
         @{ Btn='Assist'; Key='~';  Lines=@('/assist Brunnar','/attack on') }
         @{ Btn='Burn';   Key='F1'; Lines=@('/disc Crystalpalm Discipline','/alt activate 511','/disc Heel of Kanji','/disc Five Point Palm') }
         @{ Btn='Panic';  Key='F2'; Lines=@('/doability 5','/alt activate 249') }
         @{ Btn='Pull';   Key='G';  Lines=@('/target nearest','/alt activate 250','/pause 10','/doability 5') }
       )}
    @{ Slot=8; Name='Pyralis'; Class='Wizard'; Win='W8'; Role='Nuke DPS / evac'
       Socials=@(
         @{ Btn='Assist'; Key='~';  Lines=@('/assist Brunnar','/cast 1') }
         @{ Btn='Burn';   Key='F1'; Lines=@('/alt activate 511','/alt activate 1217','/alt activate 215','/cast 1','/cast 3') }
         @{ Btn='Panic';  Key='F2'; Lines=@('/alt activate 250','/cast 6') }
       )}
  )}
  @{ Team='TLP'; Lvl=65; Chars=@(
    @{ Slot=1; Name='Brunnar'; Class='Warrior'; Win='T1'; Role='Main Tank / Main Assist (driver)'
       Socials=@(
         @{ Btn='Assist'; Key='~';  Lines=@('/target Brunnar','/xtarget 1 set') }
         @{ Btn='Burn';   Key='F1'; Lines=@('/disc Defensive','/disc Provoke','/disc Weaponshield') }
         @{ Btn='Panic';  Key='F2'; Lines=@('/disc Defensive','/disc Fortitude') }
       )}
    @{ Slot=2; Name='Aelith'; Class='Cleric'; Win='T2'; Role='Primary healer (CH chain)'
       Socials=@(
         @{ Btn='Assist'; Key='~';  Lines=@('/target Brunnar','/xtarget 1 set') }
         @{ Btn='Burn';   Key='F1'; Lines=@('/cast 4','/pet attack') }
         @{ Btn='Panic';  Key='F2'; Lines=@('/cast 8','/cast 1') }
       )}
    @{ Slot=3; Name='Sylwen'; Class='Druid'; Win='T3'; Role='Backup heal / fire DPS'
       Socials=@(
         @{ Btn='Assist'; Key='~';  Lines=@('/target Brunnar','/xtarget 1 set') }
         @{ Btn='Burn';   Key='F1'; Lines=@('/cast 11','/cast 12','/cast 11') }
         @{ Btn='Panic';  Key='F2'; Lines=@('/cast 8','/cast 2') }
       )}
    @{ Slot=4; Name='Quillan'; Class='Bard'; Win='T4'; Role='DPS / haste / mez / PRIMARY PULLER'
       Socials=@(
         @{ Btn='Assist'; Key='~';  Lines=@('/assist Brunnar','/attack on','/melody 1 2 3') }
         @{ Btn='Burn';   Key='F1'; Lines=@('/cast 1','/melody 1 2 3') }
         @{ Btn='Panic';  Key='F2'; Lines=@('/twist stop','/melody 6') }
         @{ Btn='Pull';   Key='G';  Lines=@('/stand','/cast 5','/cast 6') }
       )}
    @{ Slot=5; Name='Grokk'; Class='Beastlord'; Win='T5'; Role='Pet + melee DPS / MAIN SLOW'
       Socials=@(
         @{ Btn='Assist'; Key='~';  Lines=@('/assist Brunnar','/attack on','/pet attack') }
         @{ Btn='Burn';   Key='F1'; Lines=@('/disc Bestial Fury','/cast 5','/pet attack') }
         @{ Btn='Panic';  Key='F2'; Lines=@('/pet guard','/cast 6') }
       )}
    @{ Slot=6; Name='Emberon'; Class='Magician'; Win='T6'; Role='Pet DPS / nuke / malo'
       Socials=@(
         @{ Btn='Assist'; Key='~';  Lines=@('/assist Brunnar','/pet attack','/cast 2') }
         @{ Btn='Burn';   Key='F1'; Lines=@('/cast 6','/cast 2','/pet attack') }
         @{ Btn='Panic';  Key='F2'; Lines=@('/pet guard','/cast 7') }
       )}
    @{ Slot=7; Name='Pyralis'; Class='Wizard'; Win='T7'; Role='Burst nuke / evac'
       Socials=@(
         @{ Btn='Assist'; Key='~';  Lines=@('/assist Brunnar','/cast 2') }
         @{ Btn='Burn';   Key='F1'; Lines=@('/cast 3','/cast 1','/cast 2') }
         @{ Btn='Panic';  Key='F2'; Lines=@('/cast 6','/cast 5') }
       )}
    @{ Slot=8; Name='Vesk'; Class='Rogue'; Win='T8'; Role='Melee DPS / backup pull'
       Socials=@(
         @{ Btn='Assist'; Key='~';  Lines=@('/assist Brunnar','/attack on','/doability Backstab') }
         @{ Btn='Burn';   Key='F1'; Lines=@('/disc Rogue''s Fury','/doability Backstab','/attack on') }
         @{ Btn='Panic';  Key='F2'; Lines=@('/doability Evade','/doability Hide') }
       )}
  )}
)

# =====================================================================
#  RUN
# =====================================================================
Banner
Head 'Pre-flight check'
Info "Documents folder : $Docs"
if (Test-Path $IsboxerCfgDir) { Ok "Inner Space / ISBoxer detected." }
else { Warn "Inner Space config folder not found. The build files still install; import them after you set up ISBoxer." }

Write-Host ''
Step "This will install to:  $InstallRoot"
$go = Read-Host '   Press ENTER to install (or type N to cancel)'
if ($go -match '^[Nn]') { Info 'Cancelled.'; return }

# ---------- 1. folders ----------
Head '1/7  Creating install folders'
$dirs = @('','ISBoxer-Profiles','EQ-Macros','EQ-Macros\Live','EQ-Macros\TLP','EQ-AudioTriggers','Inventory','CommandCenter','Backups')
foreach ($d in $dirs) {
  $p = if ($d) { Join-Path $InstallRoot $d } else { $InstallRoot }
  New-Item -ItemType Directory -Force -Path $p | Out-Null
}
Ok "Folder tree ready under $InstallRoot"

# ---------- 2. backup existing ISBoxer config ----------
Head '2/7  Backing up your existing ISBoxer config'
if (Test-Path $IsboxerXml) {
  $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
  $bk = Join-Path $InstallRoot "Backups\ISBoxer Toolkit ($stamp).xml"
  Copy-Item $IsboxerXml $bk -Force
  Ok "Backed up to Backups\ISBoxer Toolkit ($stamp).xml"
  Info 'Your live ISBoxer config was NOT modified.'
} else {
  Info 'No existing ISBoxer Toolkit.xml found - nothing to back up.'
}

# ---------- 3. EQ macro/social files ----------
Head '3/7  Writing EQ social/macro files (ready to paste)'
$macroCount = 0
foreach ($t in $Teams) {
  foreach ($c in $t.Chars) {
    $lines = New-Object System.Collections.Generic.List[string]
    $lines.Add('====================================================================')
    $lines.Add("  $($t.Team) TEAM  |  Box $($c.Slot) ($($c.Win))  |  $($c.Name) the $($c.Class)")
    $lines.Add("  Role: $($c.Role)")
    $lines.Add('====================================================================')
    $lines.Add('')
    $lines.Add('HOW TO USE: In EverQuest open the Socials window (Actions tab),')
    $lines.Add('pick an empty button, click EDIT, set the name + colour shown below,')
    $lines.Add('then type each line into its own row. Drag the social onto your')
    $lines.Add('hotbar in the slot that matches its hotkey. Do this once per box.')
    $lines.Add('')
    foreach ($s in $c.Socials) {
      $lines.Add('--------------------------------------------------------------------')
      $lines.Add("  SOCIAL:  $($s.Btn)        HOTKEY / HOTBAR SLOT:  $($s.Key)")
      $lines.Add('--------------------------------------------------------------------')
      $n = 1
      foreach ($ln in $s.Lines) { $lines.Add(("  {0}. {1}" -f $n, $ln)); $n++ }
      $lines.Add('')
    }
    $file = Join-Path $InstallRoot ("EQ-Macros\{0}\{1:D2}-{2}-{3}.txt" -f $t.Team, $c.Slot, $c.Class, $c.Name)
    Set-Content -Path $file -Value $lines -Encoding UTF8
    $macroCount++
  }
}
Ok "Wrote $macroCount per-character social files into EQ-Macros\Live and \TLP"

# ---------- 4. ISBoxer build recipe ----------
Head '4/7  Writing the ISBoxer build recipe'
$isb = @'
====================================================================
  MCHP BOXING - ISBoxer Toolkit build recipe
  (Build these in ISBoxer Toolkit, then Export to Inner Space.)
====================================================================

WHY A RECIPE INSTEAD OF AN AUTO-IMPORT:
  ISBoxer's saved profile (ISBoxer Toolkit.xml) is tied to YOUR exact
  game install, window names and account slots. The safest, no-corruption
  way to deliver the build is this exact recipe - it takes ~10 minutes and
  it will be correct for your machine. Your old config was already backed
  up by this installer (see the Backups folder) so you can experiment freely.

--------------------------------------------------------------------
STEP 1 - CHARACTER SETS
--------------------------------------------------------------------
  Create two Character Sets:
    * "Live8"  - add your 8 live EQ instances, assign slots 1-8 in this order:
                 1 Warrior  2 Cleric  3 Druid  4 Bard
                 5 Beastlord 6 Beastlord 7 Monk  8 Wizard
    * "TLP8"   - add your 8 TLP instances, slots 1-8:
                 1 Warrior  2 Cleric  3 Druid  4 Bard
                 5 Beastlord 6 Magician 7 Wizard 8 Rogue

--------------------------------------------------------------------
STEP 2 - ACTION TARGET GROUPS  (Mapped Keys > Action Target Groups)
--------------------------------------------------------------------
  Everyone : all 8 boxes
  AllDPS   : Beastlords, Monk/Rogue, Wizard, Magician, Bard
  Healers  : Cleric + Druid
  Casters  : Wizard, Magician, Druid, Cleric
  Tank     : Warrior
  Puller   : Monk (Live) / Bard (TLP)

--------------------------------------------------------------------
STEP 3 - MAPPED KEYS  (one physical key -> team action)
--------------------------------------------------------------------
  ~  (tilde)  "Assist"   -> send keystroke ~  to AllDPS
                            (each box's ~ social assists Brunnar + attacks)
  F1          "Burn"      -> ENABLE STEPS:
                            Step1 send F1 to Everyone (Tier 1: epics/long CDs)
                            Step2 send F1 to Everyone (Tier 2: class burn discs/AA)
                            Step3 send F1 to Everyone (Tier 3: nuke rotation)
                            "Reset steps after 12s"
  F2          "Panic"     -> send F2 to Healers, then to Tank, then to Beastlords
  G           "Pull"      -> send G to Puller only
  \           "Follow"    -> send \ to (Everyone except Tank): each runs /stick Brunnar
  F5          "Buff"      -> send F5 to Everyone (re-fire buffs/clickies)
  Pause       "Broadcast" -> toggle key broadcasting on/off  (SAFETY KEY)

  Optional:
  Shift+G     "Split"     -> FD/Fade on Puller only (peel one mob off a pack)
  Ctrl+1..8               -> jump to box 1-8 (window swap)

--------------------------------------------------------------------
STEP 4 - WINDOW LAYOUT
--------------------------------------------------------------------
  Main (Warrior) = large region. Healers + DPS on a swap-bar (Repeater region)
  so healer HP is always visible. Bind Pause = broadcast toggle and a hold key
  (`) for momentary broadcast.

--------------------------------------------------------------------
STEP 5 - EXPORT
--------------------------------------------------------------------
  Click "Export to Inner Space" in the Toolkit, then launch the Character Set.
  Paste the in-game socials from the EQ-Macros folder (one pass per box).

Recommended hardware: 2560x1440 (single ultrawide or dual monitor),
Medium UI scale. Accent colour: cyan on a dark UI (already set in the app).
====================================================================
'@
Set-Content -Path (Join-Path $InstallRoot 'ISBoxer-Profiles\MCHP-ISBoxer-Build-Recipe.txt') -Value $isb -Encoding UTF8
Ok 'Wrote ISBoxer-Profiles\MCHP-ISBoxer-Build-Recipe.txt'

# ---------- 5. audio triggers + inventory ----------
Head '5/7  Writing audio triggers + inventory layout'
$trig = @'
====================================================================
  MCHP BOXING - EQ Audio Triggers  (add in-game: Alt+A > Audio Triggers)
====================================================================
Create a trigger for each phrase below and assign a distinct sound so you
react without reading 8 chat logs. Set "match on" to the phrase text.

NAMED SPAWN ALERTS (set per camp - examples):
  Phrase: "Sontalak"                 Sound: loud chime / TTS "Named up"
  Phrase: "Overlord Mata Muram"      Sound: loud chime
  Phrase: "has been slain by"        Sound: soft tick  (kill confirm)

PROC / COOLDOWN NOTIFICATIONS:
  Phrase: "Your target is immune"    Sound: error buzz
  Phrase: "You have taunted"         Sound: low tick   (Warrior aggro)
  Phrase: "is no longer slowed"      Sound: alert      (re-slow!)

BUFF FADE TRACKING:
  Phrase: "Your Aegolism"            Sound: re-buff cue  (then press F5)
  Phrase: "has worn off"             Sound: re-buff cue
  Phrase: "Your spell fizzles"       Sound: soft tick

DANGER / PANIC CUES:
  Phrase: "You are unconscious"      Sound: alarm  (press F2 panic)
  Phrase: "has been slain"           Sound: alarm  (a box died)

TIP: In ISBoxer you can also add an "Alert" action to pop the box that
matched the trigger to the front so you instantly see who needs you.
====================================================================
'@
Set-Content -Path (Join-Path $InstallRoot 'EQ-AudioTriggers\EQ-Audio-Triggers.txt') -Value $trig -Encoding UTF8

$inv = @'
====================================================================
  MCHP BOXING - Standard inventory layout (use on ALL 8 boxes)
====================================================================
Keeping every box's bags identical means one broadcast "use clicky" or
"sell junk" macro works everywhere.

  Bag 1  Clickies & click-buffs     (slot 1 = main click-buff -> /useitem 1 1)
  Bag 2  Consumables (food/drink/potions)
  Bag 3  Class reagents / arrows / poisons
  Bag 4  Tradeskill / collectibles
  Bag 5-8  Loot (keep empty before a farm run)

Master looter on the Warrior. Clicky broadcast example: /useitem 1 1
fires the item in bag 1 slot 1 on every box at once.
====================================================================
'@
Set-Content -Path (Join-Path $InstallRoot 'Inventory\Inventory-Layout.txt') -Value $inv -Encoding UTF8
Ok 'Wrote audio-trigger list and inventory layout'

# ---------- 6. Command Center app + Start-Here ----------
Head '6/7  Installing the Command Center app'
$ccSource = $null
foreach ($cand in @((Join-Path $ScriptDir 'CommandCenter.html'), (Join-Path $ScriptDir 'index.html'), (Join-Path (Split-Path $ScriptDir -Parent) 'index.html'))) {
  if (Test-Path $cand) { $ccSource = $cand; break }
}
$ccDest = Join-Path $InstallRoot 'CommandCenter\MCHP-Command-Center.html'
if ($ccSource) {
  Copy-Item $ccSource $ccDest -Force
  Ok "Installed Command Center -> CommandCenter\MCHP-Command-Center.html"
} else {
  Warn 'Command Center HTML not found next to the installer; skipped. (Copy MCHP-Command-Center.html in manually.)'
}

$start = @"
====================================================================
  START HERE  -  MCHP Boxing ISBoxer Command Center
====================================================================
Everything is installed in:
  $InstallRoot

WHAT'S IN THE BOX:
  CommandCenter\   The visual command center app  (double-click the .html)
  ISBoxer-Profiles\  Your step-by-step ISBoxer build recipe
  EQ-Macros\Live + \TLP   Ready-to-paste socials, one file per character
  EQ-AudioTriggers\  Named/proc/buff-fade alert phrases for EQ
  Inventory\   Standard bag layout for all boxes
  Backups\   A safe copy of your previous ISBoxer config

DO THIS, IN ORDER:
  1. Open CommandCenter\MCHP-Command-Center.html (or the Desktop shortcut).
     It's your reference for the whole build.
  2. Build ISBoxer using ISBoxer-Profiles\MCHP-ISBoxer-Build-Recipe.txt
     (~10 min), then Export to Inner Space and launch a team.
  3. In EQ, paste the socials from EQ-Macros\<team>\ - one file per box.
     Drag each social to the hotbar slot shown (~, F1, F2, G).
  4. Add the audio triggers from EQ-AudioTriggers\ in-game (Alt+A).
  5. Standardise bags per Inventory\Inventory-Layout.txt.
  6. Test on green mobs: ~ assist, F1 burn, F2 panic, G pull. Done!

WHY SOCIALS AREN'T AUTO-FILLED:
  EverQuest stores socials/hotbuttons on Daybreak's servers per character,
  so no installer can write them directly. These files make it a quick
  copy-paste instead of typing everything by hand.

Support: MCHP Boxing Services
====================================================================
"@
Set-Content -Path (Join-Path $InstallRoot '00-START-HERE.txt') -Value $start -Encoding UTF8
Ok 'Wrote 00-START-HERE.txt'

# ---------- 7. desktop shortcut ----------
Head '7/7  Creating Desktop shortcut'
if ($ccSource) {
  try {
    $wsh = New-Object -ComObject WScript.Shell
    $lnk = $wsh.CreateShortcut((Join-Path $Desktop 'MCHP Command Center.lnk'))
    $lnk.TargetPath = $ccDest
    $lnk.WorkingDirectory = (Join-Path $InstallRoot 'CommandCenter')
    $lnk.Description = 'MCHP Boxing - ISBoxer Multibox Command Center'
    $lnk.Save()
    Ok 'Desktop shortcut created: "MCHP Command Center"'
  } catch { Warn "Could not create desktop shortcut: $($_.Exception.Message)" }
} else { Info 'Skipped shortcut (no Command Center file).' }

# ---------- done ----------
Write-Host ''
Line '='
Write-Host '   INSTALL COMPLETE' -ForegroundColor Green
Line '='
Info "Install folder : $InstallRoot"
Info 'Opening the Start-Here guide and the install folder...'
try { Invoke-Item (Join-Path $InstallRoot '00-START-HERE.txt') } catch {}
try { Invoke-Item $InstallRoot } catch {}
if ($ccSource) { try { Invoke-Item $ccDest } catch {} }
Write-Host ''
Write-Host '   Thank you - MCHP Boxing Services' -ForegroundColor Cyan
Write-Host ''
