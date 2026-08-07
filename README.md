# TCS-Trommeschläger-Genie-IIIs-GDos-2.4
TCS Trommeschläger Genie IIIs focus on the GDos 2.4 implementation

## Repository purpose

This repository archives and reverse-engineers disk/ROM images for the **TCS Trommeschläger Genie IIIs**, a German-made clone of the Tandy/RadioShack TRS-80 Model III/4. The focus is **GDOS 2.4** (the Genie's native DOS) and, ultimately, understanding hard-disk boot support on this platform — specifically **Arnulf Sopp's 1986 boot-EPROM modification** that adds hard-disk (OMTI controller) boot capability. This repo is scoped to GDOS/TRS-DOS-family content; CP/M material lives in the general [TCS-Trommeschlaeger-Genie-IIIs](https://github.com/Egbert-Azure/TCS-Trommeschlaeger-Genie-IIIs) archive and is intentionally not duplicated here. There is no build system or test suite — it's a disk/ROM archive plus reverse-engineering notes.

Investigation order:

1. Establish GDOS 2.4's origin and structure — **done**, see below.
2. Determine whether/how GDOS 2.4 supports hard disks — **done**: the Genie-IIIs-specific build ships `HDFORMAT.CMD`/`GENDIR.CMD`. See below.
3. Find "the new EPROM" for HD boot — **done**: `ROM/g3s_hd-omti_bootrom_2764.bin` self-identifies as modified by Arnulf Sopp in 1986 for an OMTI hard-disk controller. See below.
4. Confirm a plain floppy boot works as a baseline before touching the Sopp EPROM — **done**, see "Emulation" below.
5. Characterize what the Sopp EPROM's HD-boot code actually does — **in progress, strong first result**: the boot-time control flow (hotkey check, OMTI presence probe, device dispatch, hand-off to a hard-disk boot sector at `4200h`) has been traced and annotated. See `src/g3s_hd-omti_bootrom_2764.annotated.md` and "The Sopp EPROM" below.
6. Confirm GDOS 2.4 reaches its hard disk end-to-end — **done for drives 5/6** ~~(a third slot, drive 9, also exists in the driver code — see the correction below)~~ *(drive-9 note reverted 2026-08-07 — see the correction under "Hard-disk support")*. GDOS 2.4 and the CP/M port drive the **Xebec S1410** SASI controller, a third protocol distinct from both OMTI 5527 and WD1000/1010. This explains the OMTI crash chased at length (see `src/omti_boot_crash_investigation.md` — now qualified, see the correction there), why WD1000 attachment never worked, and why no GDOS "connect the hard disk" command was ever found (GDOS 2.4 has no user-facing configuration command for HD parameters — see the correction below on what actually populates the drive-table entry). [`sdltrs-MultiHDC`](https://github.com/Egbert-Azure/sdltrs-MultiHDC) now emulates the Xebec S1410, and GDOS 2.4's drives 5/6 work end-to-end (`HDFORMAT`, `GENDIR`, files persist across reboots). ~~Still open: the Sopp EPROM's own boot-from-hard-disk path.~~ **Resolved, 2026-08-01 — see "Open questions."**

## Contents

- Disks are shipped as raw `.dmk`/`.DMK` images; extract any of them with `trsextract` (see "Working with disk/ROM images" below).
- `README.md`, `LICENSE` (GPLv3).

All new disks/ROMs were sourced from the sibling `GenieIIIs` repo (see "External resources"); only GDOS/TRS-DOS-relevant and boot-ROM material was brought over — CP/M-only disks and source trees in that repo (Holte's CP/M 3 BIOS, its Z-System boot disk, etc.) were deliberately left out of this repo.

## Working with disk/ROM images

- Treat `.dmk` and `.bin` files as opaque binary artifacts. Extract `.dmk` disks with the [trsextract](https://github.com/Egbert-Azure/trsextract) tool (`python3 trsextract.py <image.dmk> -o <dest_dir> -v`, a custom TRS-80 NEWDOS/80 & G-DOS extractor). Falls back to `strings -n 4` / `xxd` / `cmp -l` for quick triage on both disks and ROMs.
- If new disk images are added, keep them under `DMK/`. ROM/EPROM dumps go under `ROM/`.

## Emulation

Actual booting/testing is done with the [**sdltrs-MultiHDC**](https://github.com/Egbert-Azure/sdltrs-MultiHDC) emulator (`build/sdl2trs`), a fork of SDL2TRS/xtrs that emulates three Genie IIIs hard-disk controllers — OMTI 5527, WD1000/1010, and the Xebec S1410 SASI. Pass this repo's own `DMK`/`ROM` files as arguments.

**GDOS 2.4's hard-disk path now works.** GDOS 2.4 (and Klaus Kämpf's CP/M port) drive the **Xebec S1410** SASI controller — a third protocol distinct from OMTI 5527 and WD1000/1010, which is why earlier OMTI-only testing failed **for this specific piece of software**. `sdltrs-MultiHDC` now emulates the Xebec S1410, including the TCS Genie IIIs onboard SASI adapter (ports `0x00`–`0x02`) that GDOS 2.4's resident driver probes at boot, and GDOS 2.4 reaches its built-in hard disk end-to-end: `PD 5`/`PD 6` return drive data, `HDFORMAT` completes both passes, GDOS partitions the unit into logical drives 5 and 6, and files written to them persist inside the `.hdv`. The floppy-only baseline below remains a useful sanity check against the standard boot ROM.

**Correction, 2026-08-01: "OMTI-only testing failed" does not generalize to the Sopp EPROM's own boot-time code, which is a separate piece of software from GDOS 2.4's resident driver.** The sibling project [`CalvaDos`](https://github.com/Egbert-Azure/CalvaDos) — a G-DOS 2.4 hard-disk-boot re-implementation continuing this investigation — has since run the Sopp EPROM's own hard-disk boot path against **OMTI**, extensively and successfully: a working OMTI transport, a working boot sector at `4200h`, and `run-hdboottest.sh` reaching PASS (3286+ OMTI operations, zero floppy reads, zero `RECORD NOT FOUND`). This is not in tension with the Xebec finding above — it's a different piece of software. Stock G-DOS 2.4's own *resident* driver (the code that services drives 5/6/9 once the OS is already running) genuinely drives Xebec S1410, confirmed independently by both projects. The Sopp EPROM's *own boot-time* code (the detect-and-load-a-boot-sector logic that runs before GDOS is loaded at all) genuinely drives OMTI — confirmed by this repo's own port table in `src/g3s_hd-omti_bootrom_2764.annotated.md` ("ports `40h`-`43h` match `sdltrs-MultiHDC`'s documented OMTI 5527 register range exactly") and now by CalvaDos's working end-to-end boot. See `CalvaDos/docs/development/boot-patch-inventory.md` and `CalvaDos/docs/reverse-engineering/calvados-investigation.md` for the trace.

`sdl2trs` loads `~/.sdltrs.t8c` (a global, cross-project settings file, not part of any repo) before applying CLI args, and an *omitted* flag does not clear a value already saved there — always pass every `-diskN`/`-hardN`/`-omtiN` slot explicitly (empty string `""` to clear) rather than relying on defaults, or you'll boot whatever was last left attached (e.g. running `sdl2trs --help`, which isn't a real flag, launches with zero overrides at all).

**Confirmed working baseline (floppy, no hard disk):**

Run the emulator from its own checkout, but point the ROM/disk paths at **this** repo. Replace `GDOS-REPO` with the path to this repository. Every drive slot is passed explicitly (empty `""` clears it) — see the note above about `~/.sdltrs.t8c`.

```sh
# from the sdltrs-MultiHDC emulator checkout:
./build/sdl2trs -model 1 \
  -rom   "GDOS-REPO/ROM/g3s_8501004_bootrom_2732.bin" \
  -disk0 "GDOS-REPO/DMK/G3S-GDOS24.DMK" \
  -disk1 "" -disk2 "" -disk3 "" -disk4 "" -disk5 "" -disk6 "" -disk7 "" \
  -hard0 "" -hard1 "" -hard2 "" -hard3 "" -omti0 "" -omti1 "" \
  -nofullscreen
```

Boots straight to a working **GDOS 2.4 prompt** with the standard boot banner; `DIR` and other commands work normally. This is the floppy-only baseline to compare against once the Sopp EPROM (`ROM/g3s_hd-omti_bootrom_2764.bin`) + an OMTI hard disk are attached instead of/alongside the floppy.

`-diskdebug <hexval>` (bit 0 `FDCREG`, bit 1 `FDCCMD`, bit 6 `DMK`, etc. — see `src/trs_disk.c` in `sdltrs-MultiHDC`) traces floppy-controller I/O to stdout/stderr, useful for confirming activity/progress without needing to read the emulated screen directly.

## Research notes

### GDOS 2.4 origin

- `SYS0.SYS` carries `VERSION 2.4  (C) 1984 TCS/MVC`. GDOS 2.4 is a 1984 product of TCS (Trommeschläger Computersysteme, Sankt Augustin); **MVC = Marcus von Cube**, who wrote GDOS 2.4 together with **Klaus Kämpf**.
- It was built from one shared codebase into three model-specific system disks (Genie III / IIs / IIIs) via installer job scripts (`GDOSIII.JOB` / `GDOSIIS.JOB` / `GDOSIIIS.JOB`); the disks here span roughly 1984–1985. Architecture: `GDOS.SYS` is a small boot stub, `SYS0.SYS` the resident DOS core, `SYS1–SYS29.SYS` (+ `OVL2–OVL5.SYS` on the IIIs) individually-loaded overlays. `SYS0.SYS` differs between disk instances — both "VERSION 2.4" but different patch levels.

### Hard-disk support (Genie IIIs only)

Hard-disk tooling ships only in the Genie IIIs ("GDOSIIIS") build. Per the manual, a built-in **10 MB hard disk** is addressed as **drives 5 and 6** (unit 1 / unit 2) — native SASI support, not a later bolt-on, shipping in the 1985 build a year before Sopp's 1986 OMTI boot-EPROM mod. `HDFORMAT.CMD` erases and two-pass formats the disk (talking to the controller directly); `GENDIR.CMD` rebuilds its boot directory but needs a valid drive-table entry (pointer at `4399h`) for the drive number.

~~**Correction, 2026-08-01: the driver code itself supports a third hard-disk slot, drive 9, not documented in the manual excerpt above.** `CalvaDos`'s own extraction of the *stock* Xebec driver blob (not authored by that project — pulled directly from a stock `SYS0/SYS`) decodes its parameter table as `10h,11h,12h,13h,00h,40h,41h,00h,7Fh,42h`: drive `5`→hard disk volume 0, `6`→volume 1, **`9`→volume 2**, all three dispatching to the same handler. See `CalvaDos/src/hd-driver/abi.md`, "a machine with two floppies and three hard-disk volumes at DOS drive numbers 5, 6 and 9." This does not contradict the manual's "drives 5 and 6" — that most plausibly describes what the specific 10 MB product used, one or two of three available slots — but it means "fixed 10MB, two partitions" understates what the driver code itself can address.~~ **What populates the `4399h` drive-table entry is also settled, 2026-08-01** — see "Open questions," below.

**Reverted, 2026-08-07: the 2026-08-01 drive-9 correction above is withdrawn.** It let a structural inference about a dispatch table override a period document, which was the wrong call. The G-DOS 2.4 manual (*HD-Unterstützung, nur GENIE IIIs*) documents one built-in 10 MB hard disk addressed as **drives 5 and 6** — one physical disk, two volumes, and that is the shipped machine. The stock Xebec driver's dispatch table does decode three slots reached by function codes 5, 6 and 9, and that decode is correct — but three dispatch slots is not the same claim as three volumes in the shipped product, and it cannot outrank the manual on what the machine shipped as. The original wording — "drives 5 and 6", "fixed 10 MB, two partitions" — stands as written.

The controller is the **Xebec S1410 (SASI)** — not WD1000/1010 or OMTI 5527 — targeted by both GDOS 2.4 and **Klaus Kämpf's** CP/M port. GDOS 2.4 has no user-configurable HD parameters (fixed 10 MB, two partitions). The **`PD`/PDRIVE** command is **floppy-only** (confirmed from the physical manual — it configures only floppy drive types, densities, and step timing); whatever populates a hard-disk drive-table entry is a separate, still-unidentified mechanism.

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

The plain ROM is 4 KB (2732); the Sopp ROM is 8 KB (2764), reorganized throughout (not a simple append), with the English boot messages translated to German plus an apparent added clock routine. It stays backward-compatible for floppy boot.

Disassembly (`src/g3s_hd-omti_bootrom_2764.annotated.md`) shows a **detect-and-fallback HD bootstrap**: a keyboard hotkey gates whether HD boot is attempted, a device selector (register `E` → `IX`) picks the target, and on success the ROM streams a boot sector from the OMTI controller (ports `40h`–`43h`) into RAM at `4200h` and jumps there. The ROM contains **no GDOS/Calva-DOS code** — ~~it hands off to a hard-disk boot sector that hasn't been obtained yet~~.

**Correction, 2026-08-01 — two separate claims here, and they now need separating.** The *original* CalvaDOS boot-sector artifact remains unobtained — unchanged. But the *hand-off contract* — what address, how much data, what the ROM expects to find there — is now known by direct observation, not from the missing artifact: the sibling project `CalvaDos` wrote its own boot sector for `4200h` (`src/hd-driver/omti/bootsec.asm`), watched this same Sopp EPROM load and execute it, and has since driven the boot all the way through `SYS0/SYS` and G-DOS module loading to a passing end-to-end harness (`run-hdboottest.sh`, PASS as of 2026-08-01). See `CalvaDos/docs/reverse-engineering/calvados-investigation.md`, "The boot chain, and why a hard-disk boot sector needs no loader of its own," and "It boots. G-DOS 2.4 runs from the OMTI hard disk, with a command prompt."

An OMTI-emulation crash hit while chasing this end-to-end is written up in `src/omti_boot_crash_investigation.md`. Its root cause as stated there — "the controller is really Xebec, not OMTI" — needs the same scoping correction made throughout this file: see the correction added directly in that file, and in "Emulation," above. The Xebec work itself was and remains the right fix for GDOS 2.4's own resident driver; it was the general phrasing of the root cause, not the Xebec work, that needed qualifying.

### External resources

- **[GenieIIIs](https://github.com/Egbert-Azure/GenieIIIs)** (now archived) — the original master archive this repo's GDOS 2.4 disks and both boot ROMs were pulled from. Its material has been reorganized into this repo and the general [TCS-Trommeschlaeger-Genie-IIIs](https://github.com/Egbert-Azure/TCS-Trommeschlaeger-Genie-IIIs) archive.
- **[trsextract](https://github.com/Egbert-Azure/trsextract)** (`trsextract.py`) — the extraction tool for the `.dmk` disks in this repo.
- **[sdltrs-MultiHDC](https://github.com/Egbert-Azure/sdltrs-MultiHDC)** — the emulator used for booting/testing, with OMTI 5527, WD1000/1010, and Xebec S1410 emulation. Its Xebec support is what makes GDOS 2.4's drives 5/6 reachable end-to-end (`HDFORMAT.CMD`, `GENDIR.CMD`).
- **[CalvaDos](https://github.com/Egbert-Azure/CalvaDos)** — a sibling project continuing this investigation from where it leaves off: a re-implementation of Arnulf Sopp's OMTI hard-disk boot support for G-DOS 2.4, since this repo's own artifact was never recovered. Owns the facts this repo now links to rather than restates: the working OMTI driver and transport, the boot sector at `4200h`, the drive model (`5`/`6`/`9`), and the `run-hdboottest.sh` PASS result cited in several corrections above, added 2026-08-01.

## Open questions

- ~~Re-run the Sopp EPROM's own *boot-from-hard-disk* path against the now-Xebec-capable `sdltrs-MultiHDC` (the emulator-side blocker for drives 5/6 is resolved — see "Emulation").~~ **Resolved, 2026-08-01, by the sibling project `CalvaDos`, and not against Xebec — against OMTI.** The premise that this path needed Xebec emulation was itself incomplete: the Sopp EPROM's own boot-time code drives OMTI (confirmed independently by this repo's own port table in `src/g3s_hd-omti_bootrom_2764.annotated.md` and by CalvaDos's working driver). Run extensively, end to end: working OMTI transport, a working boot sector at `4200h`, `SYS0/SYS` and G-DOS module loading, `run-hdboottest.sh` reaching PASS (3286+ OMTI operations, zero floppy reads, zero `RECORD NOT FOUND`). Not independently confirmed to reach the interactive command prompt (`Befehlseingabe`) as of that PASS — see `CalvaDos/README.md`'s own status section for the precise claim. See `CalvaDos/docs/development/boot-patch-inventory.md` and `CalvaDos/docs/reverse-engineering/calvados-investigation.md` for the full trace.
- **Split into two questions, 2026-08-01.** Does the *original* boot sector at `4200h` contain GDOS 2.4, or a distinct "Calva-DOS"? Still open — no such artifact has been obtained. Separately: what does the EPROM expect to find there, structurally? **Answered by observation, not by recovering the original artifact** — `CalvaDos` wrote a working boot sector for this address and watched this ROM load and execute it successfully; see the correction in "The Sopp EPROM," above.
- ~~What populates GDOS's hard-disk drive-table entry (needed for `GENDIR.CMD` on drives 5/6)? Confirmed **not** `PD`/PDRIVE — still unidentified.~~ **Resolved, 2026-08-01, by `CalvaDos`.** `DRVSEL` itself populates `4399h` (and the 8-byte PDRIVE copy at `430Ah`-`4311h`) as routine bookkeeping on *every* drive select, any drive — not `PD`/`PDRIVE` (correctly ruled out here), and not `GENDIR.CMD` itself, which relies on the command interpreter having already selected the drive before it runs. Two independent findings converge on this: `CalvaDos/docs/reverse-engineering/calvados-investigation.md`, "What GENDIR and HDFORMAT actually are" (2026-07-26, from reading `GENDIR/CMD` itself) and "`dsave` (`4306h`) frozen..." (2026-08-01, a full disassembly of stock `DRVSEL`'s write set, `4773h`-`47E2h`).
- Which physical key skips HD boot (`F1`/`F2` are the candidates), and does a third boot-ROM variant (Xebec/WD1000-initializing) exist? **Untouched by this correction pass** — no work in the sibling repository bears on this.
