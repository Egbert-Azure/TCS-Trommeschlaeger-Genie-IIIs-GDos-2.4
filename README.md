# TCS-Trommeschläger-Genie-IIIs-GDos-2.4
TCS Trommeschläger Genie IIIs focus on the GDos 2.4 implementation

## Repository purpose

This repository archives and reverse-engineers disk/ROM images for the **TCS Trommeschläger Genie IIIs**, a German-made clone of the Tandy/RadioShack TRS-80 Model III/4. The focus is **GDOS 2.4** (the Genie's native DOS) and, ultimately, understanding hard-disk boot support on this platform — specifically **Arnulf Sopp's 1986 boot-EPROM modification** that adds hard-disk (OMTI controller) boot capability. This repo is scoped to GDOS/TRS-DOS-family content; CP/M material lives in the separate sibling `GenieIIIs` repo and is intentionally not duplicated here. There is no build system or test suite — it's a disk/ROM archive plus reverse-engineering notes.

Investigation order:

1. Establish GDOS 2.4's origin and structure — **done**, see below.
2. Determine whether/how GDOS 2.4 supports hard disks — **done**: the Genie-IIIs-specific build ships `HDFORMAT.CMD`/`GENDIR.CMD`. See below.
3. Find "the new EPROM" for HD boot — **done**: `ROM/g3s_hd-omti_bootrom_2764.bin` self-identifies as modified by Arnulf Sopp in 1986 for an OMTI hard-disk controller. See below.
4. Confirm a plain floppy boot works as a baseline before touching the Sopp EPROM — **done**, see "Emulation" below.
5. Characterize what the Sopp EPROM's HD-boot code actually does — **in progress, strong first result**: the boot-time control flow (hotkey check, OMTI presence probe, device dispatch, hand-off to a hard-disk boot sector at `4200h`) has been traced and annotated. See `src/g3s_hd-omti_bootrom_2764.annotated.md` and "The Sopp EPROM" below.
6. Confirm the hard-disk boot path end-to-end against a real OMTI `.hdv` image — **root cause found, blocked on missing emulator support, not fixable from this repo.** GDOS 2.4 and the CP/M port both use **Xebec S1410** SASI, a third protocol distinct from both OMTI 5527 and WD1000/1010 — neither of which `sdltrsOMTI` emulates matches it. This explains the `sdltrsOMTI` crash chased at length (see `src/omti_boot_crash_investigation.md`), why WD1000 attachment never worked, and why no GDOS "connect the hard disk" command was ever found (GDOS 2.4 has no configurable HD parameters at all — fixed 10MB, two partitions, drives 5/6). **Next step is in a new sibling repo, `~/Documents/GitHub/sdltrsXebec`** (a fresh clone of `sdltrsOMTI`, not a modification to it — see that repo's own `README.md`), adding real Xebec S1410 emulation. Come back to *this* repo once that works.

## Contents

Disks are shipped as raw `.dmk`/`.DMK` images; extract any of them with `trsextract` (see "Working with disk/ROM images" below).

- `DMK/g3s_gdos24.dmk` — a **multi-model master/installer disk**: carries `GDOSIII.IDL/.JOB`, `GDOSIIS.IDL/.JOB`, and `GDOSIIIS.IDL/.JOB` side by side, i.e. the job scripts + file manifests used to build model-specific system disks (Genie III / IIs / IIIs) from one shared codebase.
- `DMK/G3S-GDOS24.DMK` — a clean **stock "GDOSIIIS" build** (96 files), matching the `GDOSIIIS.IDL` manifest from the master disk exactly: printer drivers (ITOH, STAR, SIEMENS), `OVL2–OVL5.SYS`, `SYS0–SYS29.SYS`, and **`HDFORMAT.CMD` + `GENDIR.CMD`**.
- `DMK/G3S-GDOS24-Transfer.DMK` — the same GDOSIIIS system files, on a physical disk that also happened to carry some unrelated CP/M dev-source files (`FORMAT.C`, `BIOS.H`, `STDIO.H`, assorted `.MAC`/`.SUB`, `NEWLIBC.REL`).
- `DMK/g3gd24-1.dmk` — a smaller (54-file) **GDOSIII-variant** build (extensionless system files: `ACCESS`, `INIT`, `INFOFILE`, `FORMFILE`, `JOB.CMD`), built from the `GDOSIII.JOB` script. No `HDFORMAT.CMD` (HD tooling is IIIs-specific — see below).
- `DMK/g3gd21-1.dmk`, `DMK/g3gd21-chr.dmk`, `DMK/g3nd-g01.dmk`, `DMK/GDOS.DSK` — additional Genie IIIs GDOS-family disks.
- `ROM/g3s_8501004_bootrom_2732.bin` — the standard Genie IIIs boot EPROM (4KB, 2732), by **Uwe Böker, TCS, 1984**.
- `ROM/g3s_hd-omti_bootrom_2764.bin` — **the hard-disk boot EPROM (8KB, 2764), modified by Arnulf Sopp in 1986** for an OMTI hard-disk controller. See "The Sopp EPROM" below — this is the key artifact for the Calva-DOS/HD-boot investigation.
- `src/g3s_hd-omti_bootrom_2764.raw_disasm.txt` — full linear Z80 disassembly of the Sopp EPROM (all 8192 bytes, blind/unannotated — includes data misdecoded as code outside the traced flow).
- `src/g3s_hd-omti_bootrom_2764.annotated.md` — the actually-understood control flow of that ROM, with addresses, register meanings, and an explicit "not yet traced" list. Read this before re-deriving anything about the ROM from scratch.
- `src/gdos_hd_tools.annotated.md` — disassembly notes on `HDFORMAT.CMD` and `GENDIR.CMD` (the two GDOS-side hard-disk tools): confirms `HDFORMAT.CMD` talks to the controller directly (no PDrive/GDOS-drive-table involvement, confirmation word is literally `JA`), while `GENDIR.CMD` requires a valid entry in GDOS's drive table (pointer at `4399h`) for whatever drive number you give it. Note: `PD`/PDRIVE itself is confirmed **floppy-only** (see "GDOS 2.4 origin" below) — whatever populates that drive-table entry for a hard disk is a still-unidentified, different command.
- `src/build_blank_omti_hdv.py` — builds a blank single-partition OMTI `.hdv` for `sdltrsOMTI`'s `-omti0`/`-omti1`. Defaults to 306 cyl/4 heads/17 sec/512B (~10.65MB, the classic "10MB" ST-506/MFM geometry — matches the real manual's documented 10MB built-in HD capacity); `--cyls`/`--heads`/`--secs` for other geometries. See "Emulation" below for the header-field gotcha it encodes.
- `src/genie3s_init_loader.md` — real TCS documentation of the *standard* (non-Sopp) boot loader's own dispatch logic, found by the user. Directly explains several previously-unidentified pieces of the Sopp ROM disassembly (see cross-reference section in `g3s_hd-omti_bootrom_2764.annotated.md`) — read this before re-guessing at `E`/`IX` boot-device-selector values or hotkey semantics.
- `src/omti_boot_crash_investigation.md` — full writeup of a reproducible `sdltrsOMTI` crash blocking end-to-end HD-boot testing, what's been ruled out (with evidence), the hotkey mechanism and open leads, and the next-step plan. Read this before resuming step 6 of the investigation order above.
- `boot_gdos24_omti.command`, `boot_gdos24_omti_stdrom.command`, `boot_gdos24_hard0.command` — one-click launchers (repo root) for `sdltrsOMTI`'s `sdl2trs`, pre-wired to this repo's own ROM/DMK/HDV files with every drive slot explicit. `_stdrom` uses the plain ROM instead of the Sopp EPROM; `_hard0` attaches the disk via the WD1000/1010 ("Xebec-style") controller instead of OMTI. See "Emulation" for why each exists.
- `README.md`, `LICENSE` (GPLv3).

All new disks/ROMs were sourced from the sibling `GenieIIIs` repo (see "External resources"); only GDOS/TRS-DOS-relevant and boot-ROM material was brought over — CP/M-only disks and source trees in that repo (Holte's CP/M 3 BIOS, its Z-System boot disk, etc.) were deliberately left out of this repo.

## Working with disk/ROM images

- Treat `.dmk` and `.bin` files as opaque binary artifacts. Extract `.dmk` disks with `python3 ~/Documents/GitHub/trsextract/trsextract.py <image.dmk> -o <dest_dir> -v` (a custom TRS-80 NEWDOS/80 & G-DOS extractor). Falls back to `strings -n 4` / `xxd` / `cmp -l` for quick triage on both disks and ROMs.
- If new disk images are added, keep them under `DMK/`. ROM/EPROM dumps go under `ROM/`.

## Emulation

Actual booting/testing is done with `~/Documents/GitHub/sdltrsOMTI` (`build/sdl2trs`), a fork of SDL2TRS/xtrs with added OMTI 5527 hard-disk-controller emulation for the Genie IIIs — see that repo's own `README.md` for its architecture. **Treat that repo as read-only from here**: only execute its prebuilt binary; never write into it (no new files, no git operations) — it has its own separate, valuable, hard-won working state (CP/M/OMTI investigation) that this repo's work must not disturb. Always pass this repo's own `DMK`/`ROM` files as arguments, never files from `~/Documents/GitHub/GenieIIIs` or `sdltrsOMTI` directly.

**`sdltrsOMTI` cannot boot GDOS 2.4's actual hard-disk path** — root cause found: GDOS 2.4 (and Klaus Kaempf's CP/M port) use the **Xebec S1410** SASI controller, which `sdltrsOMTI` does not emulate (it has OMTI 5527 and WD1000/1010 only, both distinct protocols). New sibling repo **`~/Documents/GitHub/sdltrsXebec`** (a separate writable fork of `sdltrsOMTI`, not a modification to it) is where Xebec S1410 emulation is being added — see that repo's own `README.md`. Until that work lands, `sdltrsOMTI` here remains useful only for floppy-only boot testing (confirmed baseline below); do not expect hard-disk boot to work against it.

`sdl2trs` loads `~/.sdltrs.t8c` (a global, cross-project settings file, not part of any repo) before applying CLI args, and an *omitted* flag does not clear a value already saved there — always pass every `-diskN`/`-hardN`/`-omtiN` slot explicitly (empty string `""` to clear) rather than relying on defaults, or you'll boot whatever was last left attached (e.g. running `sdl2trs --help`, which isn't a real flag, launches with zero overrides at all).

**Confirmed working baseline (floppy, no hard disk):**

```sh
cd ~/Documents/GitHub/sdltrsOMTI
./build/sdl2trs -model 1 \
  -rom "<this-repo>/ROM/g3s_8501004_bootrom_2732.bin" \
  -disk0 "<this-repo>/DMK/G3S-GDOS24.DMK" \
  -disk1 "" -disk2 "" -disk3 "" -disk4 "" -disk5 "" -disk6 "" -disk7 "" \
  -hard0 "" -hard1 "" -hard2 "" -hard3 "" -omti0 "" -omti1 "" \
  -nofullscreen
```

Boots straight to a working **GDOS 2.4 prompt** with the standard boot banner; `DIR` and other commands work normally. This is the floppy-only baseline to compare against once the Sopp EPROM (`ROM/g3s_hd-omti_bootrom_2764.bin`) + an OMTI hard disk are attached instead of/alongside the floppy.

`-diskdebug <hexval>` (bit 0 `FDCREG`, bit 1 `FDCCMD`, bit 6 `DMK`, etc. — see `src/trs_disk.c` in `sdltrsOMTI`) traces floppy-controller I/O to stdout/stderr, useful for confirming activity/progress without needing to read the emulated screen directly.

## Research notes

### GDOS 2.4 origin

- `SYS0.SYS` carries `VERSION 2.4  (C) 1984 TCS/MVC`. GDOS 2.4 is a 1984 product of **TCS/MVC** (TCS = Trommeschläger Computersysteme / TCS Computer GmbH, Sankt Augustin; "MVC" credit unexpanded).
- GDOS 2.4 was built from **one shared codebase producing three model-specific system disks** — Genie III, Genie IIs, and Genie IIIs — via an installer job script (`GDOSIII.JOB` / `GDOSIIS.JOB` / `GDOSIIIS.JOB`, each: `COPY 0 1,,EDK FMT KDWA IDL=<model>/IDL` then `PROT 1 NAME=<model>F`). The `<model>.IDL` file is the resulting manifest (name/date + file list) copied onto the new disk; `GDOS.ILF`/`INHALT.SYS`/`DIR.SYS` play the same directory-manifest role on the already-built disks.
- Install-manifest dates found: `17.04.85` (master disk, all three `.IDL` files) and `15.09.85` (an older accumulated GDOS 2.4 system disk, investigated separately) — so the material spans roughly Sept 1984 (code copyright) through at least Sept 1985 (an install/rebuild instance).
- Architecture: `GDOS.SYS` (~1280 bytes) is a small boot stub; `SYS0.SYS` (19200 bytes) is the large resident DOS core; `SYS1–SYS29.SYS` (~1.2–1.3KB each) are individually-loaded overlay modules (error text, printer routing, formatting, etc., mostly in German). The Genie-IIIs build additionally uses `OVL2–OVL5.SYS`.
- **The DOS core is not a single fixed binary.** `SYS0.SYS` differs by 1719 of 19200 bytes between an older accumulated GDOS 2.4 system disk (investigated separately) and the stock GDOSIIIS build (`G3S-GDOS24.DMK`), spread across the whole file — both self-identify as "VERSION 2.4" but are different internal builds/patch levels.

### Hard-disk support in GDOS 2.4 — Genie-IIIs-specific

GDOS 2.4 ships hard-disk tooling, but only in the Genie IIIs ("GDOSIIIS") build, not in the IIs or III builds (their `.IDL` manifests / extracted file sets have no equivalent). **From the real manual (photographed by the user): "Eine im GENIE IIIs eingebaute 10 MByte Harddisk wird von G-DOS 2.4 unterstützt. Die HD wird mit den Laufwerksnummern 5 und 6 angesprochen."** — a 10MB hard disk built into the Genie IIIs is supported by G-DOS 2.4, addressed as **drive numbers 5 and 6**. This directly answers "which drive is the HD" and confirms HD support (via SASI) was native to G-DOS 2.4, not a later bolt-on — matches the tooling shipping in the 1985 stock Genie-IIIs build, a year before Sopp's 1986 OMTI EPROM mod. The two drive numbers almost certainly correspond to the "unit 1 / unit 2" distinction found in `HDFORMAT.CMD`'s own disassembly (see below) — drive 5 = unit 1 (default), drive 6 = unit 2 (selected by typing `2` as the third confirmation character). `src/build_blank_omti_hdv.py` defaults to the matching 10MB/306-cylinder geometry.

- **`HDFORMAT.CMD`** (219 bytes): prompts `Wollen Sie die HARDDISK tatsächlich löschen?` ("Do you really want to erase the HARDDISK?"), then runs a two-pass format+verify (`Durchgang 1` / `Durchgang 2`).
- **`GENDIR.CMD`** (800 bytes): (re)builds a boot directory referencing `BOOT/SYS`, `GDOS/SYS`, `INHALT/SYS` and a `GDOS 00.00.00` version tag; errors with `Schlechte PDrive-Daten` ("Bad PDrive data") if the drive-table entry (pointer at `4399h`) for the drive number you give it isn't valid — now known to be drive `:5` or `:6`. **Correction from an earlier pass**: the `PD` command/table itself (see below) is confirmed 100% floppy-only from the real GDOS manual — so this is *not* evidence that PDrive covers hard disks too. Whatever actually populates a hard-disk-capable entry in that same drive table is a different, still-unidentified mechanism.
- Both tools are small and almost certainly call into BIOS-resident routines in `SYS0.SYS`/the overlays for the actual low-level disk I/O, rather than containing full controller-level logic themselves.
- **The controller is a Xebec S1410 (SASI), confirmed by the user**: both GDOS 2.4 and Klaus Kaempf's CP/M port for the Genie IIIs target Xebec S1410 SASI specifically — not WD1000/1010, and not OMTI 5527 either (though "somewhat more similar" to OMTI). See `src/omti_boot_crash_investigation.md`'s root-cause section — this is why end-to-end emulator testing has been blocked, and it isn't fixable from this repo. **GDOS 2.4 has no configurable hard-disk parameters at all**: fixed 10MB, two partitions (drives 5/6), nothing user-settable — consistent with `PD` being confirmed floppy-only and with no "connect the hard disk" GDOS command ever being found.

### The `PD` command is floppy-only (confirmed from the real GDOS manual)

The real GDOS 2.4 manual exists on archive.org, mislabeled — the item is titled "GDOS v2.4 1984 TCS Computer" but its actual OCR'd content self-identifies as the **G-DOS 2.1b manual** and covers floppy operation only (fetched via `https://archive.org/download/GDOS_v2.4_1984_TCS_Computer/GDOS_v2.4_1984_TCS_Computer_djvu.txt`, redirects to a `dn760103.eu.archive.org` host — the OCR text has zero hits for PDRIVE/HDFORMAT/GENDIR/hard disk anywhere). The `PD`/PDRIVE **command syntax itself** was supplied directly by the user from physical manual pages (not in that archive.org copy) and is fully floppy-specific:

- `PD <drive>` displays that drive's parameter table (10 rows, `0`-`9`); `PD <drive> A` reapplies/redisplays; `PD <drive> <row>=<value>` copies a whole row; `PD <drive> <row> <field>=<value>[,...] A` edits specific fields of a row, with `A` making the change effective immediately instead of only after the next system start.
- Fields: `TI` = floppy **controller chip** compatibility (`TI=A`/`B`/`C`, gating which `TD` values are legal — FDC1771 vs FDC1771-or-1791), with optional appended single-letter modifier flags `H`/`I`/`J`/`K`/`L`/`M` (head-load delay, sector-numbering-from-1, track-numbering-from-1, mixed first-track density, double-step for 40-track media on 80-track drives, TRS-80 Model III-format compatibility — all floppy-only concepts). `TD` = drive type (`A`-`H`, single/double density × single/double-sided × 5.25"/8"). `SP` = track count. `SEK` = sectors per track (must be even for double-sided). `SWZ` = head-step timing (0-3 → 5/10/20/40ms). `EIB`/`SBIV`/`AEIV` = directory allocation-block size/location/count (5-sector, 256-byte-sector blocks).
- **None of this has a hard-disk mode.** An earlier pass through this investigation misread the live screen's `TI=EHK` as suggesting `TI=K` meant "hard disk" — wrong; the real syntax is `TI=CK` (base type `C` + the `K` mixed-density flag) and `K` is explicitly floppy ("first track single-density"). Live `PD 0` on the actual running system shows 10 default rows, all with `TD`/`SP`/`SEK` values in floppy ranges (max `SP=80` tracks) — none configured as a hard disk.
- **Conclusion: whatever populates GDOS's drive table for a hard disk is not `PD`/PDRIVE.** Still unidentified — not `PDRIVE.CMD`/`ID.CMD`/`IDENT.CMD`/`DDSD.CMD` either (all confirmed floppy-density-autodetect tools ported from NEWDOS-80). This blocks `GENDIR.CMD` (see above), though not `HDFORMAT.CMD`, which bypasses the drive table entirely.

### The Sopp EPROM — `ROM/g3s_hd-omti_bootrom_2764.bin`

This is the headline finding: **the boot ROM itself names Arnulf Sopp as the author of the hard-disk boot modification.** `strings` on it shows:

```text
(R)  1984 TCS #8601003
(C)  1984 Uwe Böker
mod. 1986 Arnulf Sopp
...
Uwe Böker   1984
Arnulf Sopp 1986
```

versus the plain `ROM/g3s_8501004_bootrom_2732.bin`, which shows only:

```text
(R) 1984   TCS
(C) 1984 U.Böker
Reg.Nr.: 8501004
```

Comparison:

- **Size**: the plain ROM is a 4KB 2732 EPROM; the Sopp/OMTI ROM is an 8KB 2764 EPROM — twice the space, consistent with added hard-disk boot code.
- **Authorship chain**: Uwe Böker wrote the original 1984 TCS boot ROM; Arnulf Sopp modified it in 1986 (registration/part number changed from `8501004` to `#8601003`, i.e. an `85` (1985)→`86` (1986) date-coded part number, matching the "mod. 1986" credit).
- **Language**: the plain ROM's error/status messages are English (`Memory-Test Bank:`, `Illegal Command`, `Boot-Error`, `No System`, `No BASIC`); the Sopp ROM's equivalent messages are the same content **translated to German** (`Speichertest Bank:`, `falscher Funktionsaufruf`, `Boot-Fehler`, `kein System`, `kein BASIC`) plus new strings not present in the plain ROM at all — German weekday abbreviations `MoDiMiDoFrSaSo`, suggesting an added date/clock routine (plausible for a hard-disk system, which would need a persistent-clock or format-timestamp feature — see `GENDIR.CMD`'s `GDOS 00.00.00` version/date tag above).
- **Not a simple append**: byte-comparing the two ROMs shows they are **not** identical-prefix-plus-extra-code — 3645 of the first 4096 bytes already differ, though the very first instructions (`F3 31` = `DI; LD SP,...`) and overall boot-vector shape match. Sopp's modification reorganized/relocated code throughout, not just appended an OMTI driver at the end.
- This is very likely the literal "new EPROM" referenced in this investigation's original goal (Sopp's hard-disk-boot modification for the Genie IIIs). Still open: whether "Calva-DOS" is a distinct DOS/name for the combination of this EPROM + GDOS + a hard disk, or something further beyond this ROM.

**Confirmed empirically**: booting `DMK/G3S-GDOS24.DMK` (floppy) under this ROM instead of the plain one produces the exact same GDOS 2.4 boot banner and a working prompt — the Sopp ROM is backward-compatible for floppy boot. `-diskdebug`/`-io` tracing during that boot showed exactly one OMTI-port access (`trs_omti_in(42) => FF`, i.e. "no controller present") before it falls through to the normal floppy path — the first concrete sign of the detect-and-fallback logic later confirmed by disassembly below.

**Static disassembly (`src/g3s_hd-omti_bootrom_2764.annotated.md`) confirms the full boot-decision architecture:**

1. **A genuine keyboard hotkey.** One byte of the keyboard matrix (address `38A0h`) is read once at the very start of boot and latched; it's re-tested at three separate points (`1100h`, `0070h`, `0042h`) to decide whether hard-disk boot is even attempted, or skipped straight to floppy. This is exactly the "hotkey to force floppy boot instead of HD" mechanism recalled going into this investigation — confirmed to exist, though the exact physical key isn't identified yet (needs the Genie IIIs keyboard matrix wiring).
2. **An explicit device selector.** Register `E` picks a boot target via `IX`: `E=1` (set only after the OMTI controller responds correctly to a real command, not just a status ping) → `IX=4200h` (hard disk); `E=3` → `IX=0000h` (almost certainly "re-enter the standard ROM's own reset vector", i.e. plain floppy boot); `E=2` → `IX=FC00h` (a third, unidentified target).
3. **A classic two-stage hard-disk bootstrap.** On success, the ROM has the OMTI controller stream a sector of real data directly into RAM at `4200h` (`INI` block-input straight from the OMTI data port) and jumps there. **The ROM itself contains no GDOS or Calva-DOS code** — it only loads and hands off to whatever boot-sector code lives in the hard disk's own first sector(s), which is a separate, not-yet-obtained artifact.
4. All of this talks to OMTI ports `40h`-`43h`, matching `sdltrsOMTI`'s own OMTI emulation exactly.

Not yet resolved: what `IX=FC00h` (`E=2`) is; which physical key produces the hotkey override; the exact SASI command bytes used for the presence probe and boot-sector read; and the contents of the relocated RAM code blocks (only reconstructed indirectly so far, from where they jump back into ROM). See the annotated file's own "Not yet traced" section for the full list.

**Second empirical confirmation, with a real (blank) OMTI hard disk attached**: `src/build_blank_omti_hdv.py` builds a blank single-partition OMTI `.hdv` (615 cyl / 4 heads / 17 sectors/track / 512 B — Seagate ST-225 geometry, one partition). Booting `G3S-GDOS24.DMK` under the Sopp ROM with this blank disk on `-omti0` produces, on screen: the boot-EPROM banner appears briefly (it attempts hard-disk boot), then — since the disk has no valid boot sector yet — it **fails and falls back to the GDOS floppy**, exactly matching the traced `1130h: JP 3800h` fallback path. The OMTI trace confirms the controller was genuinely detected this time (`trs_omti_in(42) => FA`, matching the disassembly's `CP FAh` check) and issued a real `command 0x00` (TEST UNIT READY). This validates the disassembly against real behavior, not just static reading.

**Reed-header gotcha** (cost one failed attach + fix): `.hdv` header byte 29 (`sec`) is sectors **per cylinder** (i.e. `heads × sectors_per_track`), not sectors per track — `sdltrsOMTI`'s `omti_open()` (`src/trs_omti.c`) does `secs / heads` and requires it to divide evenly. `68` (`4 heads × 17 sec/track`), not `17`, for this geometry. Get this wrong and attach fails with `unusable geometry (N heads/M secs)` and the emulator silently runs as if nothing were attached at all — always check the log for that message after attaching a freshly-built `.hdv`.

**A real, 100%-reproducible crash — investigated in depth, root cause not yet found.** With the blank OMTI disk correctly attached, once the ROM's OMTI-detect sequence gets far enough to actually complete a real SASI READ (512 bytes transferred correctly, status correctly reports success), the very next instruction — a plain `RET` that should return cleanly to the floppy-fallback path — instead lands the Z80 program counter at a garbage address (`002Bh`) and the emulator spins forever decoding junk as floppy-port writes (`trs_disk_command(0x2B) not implemented - bogus drive select`, endlessly). Extensive cross-referencing against `sdltrsOMTI`'s actual source ruled out GDOS, the ROM's own logic, the OMTI protocol state machine (`trs_omti.c` — proven byte-for-byte correct), a port-collision in `trs_io.c`, and two interrupt mechanisms (motor-off NMI explicitly disabled for `-model 1`; regular IRQ blocked by the ROM's own `DI` with no matching `EI` in the executed path). Root cause is narrowed to something lower-level (Z80 core `INI`/`OTIR` handling, or `trs_memory.c` bank-switching) but not confirmed — live single-step debugging would be needed, and three different scripted attempts to drive `zbx`'s breakpoints this session all failed to actually pause execution. **Full writeup, everything ruled out with evidence, and the next-step plan: `src/omti_boot_crash_investigation.md`.** Read that before spending more time on this.

### External resources

- **`~/Documents/GitHub/GenieIIIs`** (local clone of `github.com/Egbert-Azure/GenieIIIs`) is the master archive this repo's GDOS 2.4 disks and both boot ROMs were pulled from. It holds substantially more material not brought into this repo (by design — this repo stays GDOS/TRS-DOS-scoped): a separate CP/M 3 + Z-System boot disk and BIOS source tree, hard-disk volume images (`HDV/*.hdv`), and other unrelated NEWDOS/MS-DOS disks. Revisit it if the Sopp-EPROM disassembly needs cross-referencing against real hardware I/O addresses.
- **`python3 ~/Documents/GitHub/trsextract/trsextract.py`** — the extraction tool for the `.dmk` disks in this repo.
- **`~/Documents/GitHub/sdltrsXebec`** — writable fork of `sdltrsOMTI`, created to add real Xebec S1410 SASI emulation (the controller GDOS 2.4/CP/M on the Genie IIIs actually use — see "The Sopp EPROM" below and `src/omti_boot_crash_investigation.md`). Once that emulation works, come back here to resume end-to-end HD-boot testing (`HDFORMAT.CMD`, `GENDIR.CMD`, drives 5/6).

## Open questions

- **What causes the `sdltrsOMTI` crash blocking end-to-end HD-boot testing?** Root cause found — `sdltrsOMTI` doesn't emulate the Xebec S1410 SASI controller GDOS 2.4 actually uses (see `src/omti_boot_crash_investigation.md`). Current top-priority blocker is now writing that emulation in `~/Documents/GitHub/sdltrsXebec` (see "Emulation" above), not further investigation in this repo.
- Does the hard-disk boot sector the Sopp ROM hands off to (at `4200h`) actually contain GDOS 2.4, or does it chain to something else entirely ("Calva-DOS" as a distinct product)? Not resolved — no such boot sector/hard-disk image has been obtained or built yet.
- Which physical key actually skips HD boot? **Confirmed `F1`/`F2` are the two candidate bits (via `sdltrsOMTI`'s own keyboard-mapping source), but `F1` may be "consumed" by the base loader's own inherited "enter Monitor" check** (per `src/genie3s_init_loader.md`) rather than doing what's wanted — `F2` is the untried, better candidate. Not yet confirmed live.
- What actually populates GDOS's drive table with a hard-disk entry (needed for `GENDIR.CMD`, drive `:5`/`:6`)? Confirmed **not** `PD`/PDRIVE (floppy-only, see above) and not `PDRIVE.CMD`/`ID.CMD`/`IDENT.CMD`/`DDSD.CMD` either. Unidentified.
- The relocated RAM code blocks (executed from `3800h`/`F700h`/`4000h` after various `LDIR`s) have only been reconstructed indirectly; a live, interactive `zbx` trace with breakpoints would resolve them directly.
- Does the Sopp ROM's `B2h` compatibility check (at `0xFFFF`) relate to the base loader's own `2FFFh`/`B2h` foreign-disk-format check (see `src/genie3s_init_loader.md`), or is it an independent reuse of the same signature value? Not reconciled.
- No Calva-DOS binary/disk beyond this ROM has been identified yet.
- "MVC" (GDOS 2.4 co-credit) is still unexpanded.
- A possible **third boot ROM variant** (WD1000/Xebec-initializing, paralleling what the Sopp ROM does for OMTI) may exist and hasn't been searched for yet — see `src/omti_boot_crash_investigation.md`.
