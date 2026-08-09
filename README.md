# TCS-Trommeschläger-Genie-IIIs-GDos-2.4

TCS Trommeschläger Genie IIIs, focused on the G-DOS 2.4 implementation.

## Repository purpose

This repository archives and reverse-engineers disk and ROM images for the **TCS Trommeschläger Genie IIIs**, a German-made machine in the Tandy TRS-80 Model III/4 family. The focus is **G-DOS 2.4**, the Genie's native DOS, and hard-disk boot support on this platform — specifically **Arnulf Sopp's 1986 boot-EPROM modification** that adds hard-disk boot via an OMTI controller.

Scope is G-DOS/TRS-DOS-family material. CP/M content lives in the general [TCS-Trommeschlaeger-Genie-IIIs](https://github.com/Egbert-Azure/TCS-Trommeschlaeger-Genie-IIIs) archive and is deliberately not duplicated here. There is no build system and no test suite — this is a disk/ROM archive plus reverse-engineering notes.

## Investigation status

| # | Question | Status |
|---|---|---|
| 1 | G-DOS 2.4's origin and structure | Settled |
| 2 | Whether/how G-DOS 2.4 supports hard disks | Settled — the Genie IIIs build ships `HDFORMAT.CMD` and `GENDIR.CMD` |
| 3 | Locate the HD-boot EPROM | Settled — `ROM/g3s_hd-omti_bootrom_2764.bin` self-identifies as modified by Arnulf Sopp in 1986 |
| 4 | Floppy-boot baseline before touching the Sopp EPROM | Settled — see "Emulation" |
| 5 | What the Sopp EPROM's HD-boot code does | Traced and annotated; see `src/g3s_hd-omti_bootrom_2764.annotated.md` |
| 6 | Whether stock G-DOS 2.4 reaches its hard disk end-to-end | Settled for drives 5 and 6, via Xebec S1410 emulation |
| 7 | Whether the Sopp EPROM's own boot path completes | **Open** — see below |

Question 7 is the live one. It is being worked in the sibling project [CalvaDOS](https://github.com/Egbert-Azure/CalvaDOS), which reconstructs the boot support Sopp wrote, since the original artifact has never been recovered.

## Contents

- Disks ship as raw `.dmk`/`.DMK` images. Extract with [trsextract](https://github.com/Egbert-Azure/trsextract): `python3 trsextract.py <image.dmk> -o <dest_dir> -v`.
- `README.md`, `LICENSE` (GPLv3).

New disks go under `DMK/`; ROM and EPROM dumps under `ROM/`. All images were sourced from the sibling `GenieIIIs` repo (see "External resources"); only G-DOS/TRS-DOS-relevant and boot-ROM material was brought across.

## Working with disk/ROM images

Treat `.dmk` and `.bin` files as opaque binaries. `trsextract` handles the disks; `strings -n 4`, `xxd` and `cmp -l` are adequate for quick triage on both disks and ROMs.

## Emulation

Booting and testing is done with [**sdltrs-MultiHDC**](https://github.com/Egbert-Azure/sdltrs-MultiHDC) (`build/sdl2trs`), a fork of SDL2TRS/xtrs that emulates three Genie IIIs hard-disk controllers: OMTI 5527, WD1000/1010, and Xebec S1410 SASI.

### Two different pieces of software, two different controllers

This distinction caused a long detour and is worth stating plainly up front:

- **Stock G-DOS 2.4's resident driver** — the code servicing drives 5 and 6 once the OS is running — drives the **Xebec S1410** SASI controller, including the Genie IIIs onboard SASI adapter at ports `00h`–`02h`. Confirmed independently by this repo and by Klaus Kämpf's CP/M port targeting the same controller.
- **The Sopp EPROM's boot-time code** — the detect-and-load logic that runs before G-DOS exists in memory — drives **OMTI**. Confirmed from this repo's own disassembly: ports `40h`–`43h` match `sdltrs-MultiHDC`'s documented OMTI 5527 register range exactly.

These are not in tension. They are separate programs written two years apart against different hardware. Earlier notes here stated "OMTI testing failed" without that qualifier, which was true of the resident driver and false of the EPROM.

With Xebec emulation in place, stock G-DOS 2.4 reaches its built-in hard disk end-to-end: `PD 5`/`PD 6` return drive data, `HDFORMAT` completes both passes, G-DOS addresses the unit as logical drives 5 and 6, and files written there persist inside the `.hdv`.

### Settings-file trap

`sdl2trs` loads `~/.sdltrs.t8c` — a global, cross-project settings file belonging to no repository — before applying command-line arguments. An *omitted* flag does not clear a value already stored there. Always pass every `-diskN`/`-hardN`/`-omtiN` slot explicitly, using an empty string to clear, or you will boot whatever was last attached. Note that `sdl2trs --help` is not a real flag and launches the emulator with no overrides at all.

### Confirmed floppy baseline

Run the emulator from its own checkout, pointing ROM and disk paths at this repo. Replace `GDOS-REPO` with the path to this repository.

```sh
# from the sdltrs-MultiHDC emulator checkout:
./build/sdl2trs -model 1 \
  -rom   "GDOS-REPO/ROM/g3s_8501004_bootrom_2732.bin" \
  -disk0 "GDOS-REPO/DMK/G3S-GDOS24.DMK" \
  -disk1 "" -disk2 "" -disk3 "" -disk4 "" -disk5 "" -disk6 "" -disk7 "" \
  -hard0 "" -hard1 "" -hard2 "" -hard3 "" -omti0 "" -omti1 "" \
  -nofullscreen
```

This boots to a working G-DOS 2.4 prompt with the standard banner; `DIR` and other commands behave normally. It is the reference point to compare against when the Sopp EPROM and an OMTI disk are attached instead.

`-diskdebug <hexval>` traces floppy-controller I/O to stdout/stderr (bit 0 `FDCREG`, bit 1 `FDCCMD`, bit 6 `DMK` — see `src/trs_disk.c` in `sdltrs-MultiHDC`). Useful for confirming activity without reading the emulated screen.

## Research notes

### G-DOS 2.4 origin

`SYS0.SYS` carries `VERSION 2.4  (C) 1984 TCS/MVC`. G-DOS 2.4 is a 1984 product of TCS (Trommeschläger Computersysteme, Sankt Augustin). **MVC is Marcus von Cube**, who wrote G-DOS 2.4 together with **Klaus Kämpf**.

It was built from one shared codebase into three model-specific system disks (Genie III / IIs / IIIs) via installer job scripts — `GDOSIII.JOB`, `GDOSIIS.JOB`, `GDOSIIIS.JOB`. The disks here span roughly 1984–1985.

Architecture: `GDOS.SYS` is a small boot stub, `SYS0.SYS` the resident DOS core, `SYS1`–`SYS29.SYS` plus `OVL2`–`OVL5.SYS` on the IIIs are individually loaded overlays. `SYS0.SYS` differs between disk instances — all "VERSION 2.4", but at different patch levels.

### Hard-disk support (Genie IIIs only)

Hard-disk tooling ships only in the Genie IIIs build. Per the G-DOS 2.4 manual (*HD-Unterstützung, nur GENIE IIIs*), a built-in **10 MB hard disk** is addressed as **drives 5 and 6** — one physical disk, two volumes. This is native SASI support present in the 1985 build, a year before Sopp's OMTI boot-EPROM modification, not a later bolt-on.

`HDFORMAT.CMD` erases and two-pass formats the disk, talking to the controller directly. `GENDIR.CMD` rebuilds the boot directory but requires a valid drive-table entry (pointer at `4399h`) for the drive number.

The controller is the **Xebec S1410 (SASI)**. G-DOS 2.4 exposes no user-configurable hard-disk parameters — the geometry is fixed. The `PD`/PDRIVE command is **floppy-only**; this is confirmed from the physical manual, which shows it configuring floppy drive types, densities and step timing and nothing else.

What populates the `4399h` drive-table entry is `DRVSEL` itself, as routine bookkeeping on every drive select for any drive — along with the 8-byte PDRIVE copy at `430Ah`–`4311h`. Not `PD`/PDRIVE, and not `GENDIR.CMD`, which relies on the command interpreter having already selected the drive before it runs. Two independent readings converge on this: `GENDIR/CMD` itself, and a full disassembly of stock `DRVSEL`'s write set at `4773h`–`47E2h`. Confidence: high — both readings are of stock code, not of reconstructed code.

**A note on the dispatch table.** The stock Xebec driver's parameter table decodes as `10h,11h,12h,13h,00h,40h,41h,00h,7Fh,42h`, giving dispatch slots reached by function codes 5, 6 and 9. That decode is correct. It is *not* a statement about how many volumes the machine shipped with — three dispatch slots and three configured volumes are different claims, and the manual settles the second one at two. Do not carry a "5/6/9" formulation into any description of the stock hard-disk layout.

### The Sopp EPROM — `ROM/g3s_hd-omti_bootrom_2764.bin`

The boot ROM names its own author. `strings` shows:

```text
(R)  1984 TCS #8601003
(C)  1984 Uwe Böker
mod. 1986 Arnulf Sopp
...
Uwe Böker   1984
Arnulf Sopp 1986
```

The plain `ROM/g3s_8501004_bootrom_2732.bin` shows only:

```text
(R) 1984   TCS
(C) 1984 U.Böker
Reg.Nr.: 8501004
```

The plain ROM is 4 KB (2732); the Sopp ROM is 8 KB (2764), reorganized throughout rather than simply appended to, with the English boot messages translated to German and an apparent added clock routine. It remains backward-compatible for floppy boot.

The disassembly (`src/g3s_hd-omti_bootrom_2764.annotated.md`) shows a detect-and-fallback hard-disk bootstrap:

1. Hotkey bits gate whether HD boot is attempted at all (`1100h`).
2. Poll port `42h` for `FAh` — card present.
3. Bus reset (`XOR A` / `OUT 41h` / `OUT 43h`), issued before the first command, never as a bare release.
4. TEST UNIT READY probe, up to 32 retries.
5. SET DRIVE CHARACTERISTICS — payload decodes to 612 cylinders, 2 heads, precomp cylinder 300. At 17 sectors per track that is 20,808 sectors, consistent with the manual's 10 MB drive.
6. Boot-sector READ, one block at cylinder/head/sector 0/0/0, streamed into `4200h` as 2 × 256 bytes.
7. `E=1`, `IX=4200h`, jump back into the relocated device-dispatch body, which hands control to `4200h`.

The device selector in register `E` picks the target: `E=1` → `IX=4200h` (hard disk), `E=2` → `IX=FC00h` (CP/M floppy), `E=3` → `IX=0000h` (service disk).

The ROM contains no G-DOS or CalvaDOS code of its own. It loads a boot sector and jumps to it.

**The original boot sector has not been recovered.** What the ROM *expects* to find at `4200h` — the address, the 512-byte size, the entry conditions — is known by direct observation of the ROM, independent of the missing artifact.

An OMTI-emulation crash encountered while chasing this is written up in `src/omti_boot_crash_investigation.md`. Its stated root cause — "the controller is really Xebec, not OMTI" — needs the scoping correction described under "Emulation" above: true of the resident driver, not of the EPROM. The Xebec work was and remains correct; it was the generality of the phrasing that was wrong.

### External resources

- **[GenieIIIs](https://github.com/Egbert-Azure/GenieIIIs)** (archived) — the original master archive these disks and both boot ROMs came from.
- **[trsextract](https://github.com/Egbert-Azure/trsextract)** — extraction tool for the `.dmk` disks here.
- **[sdltrs-MultiHDC](https://github.com/Egbert-Azure/sdltrs-MultiHDC)** — the emulator used for booting and testing, with OMTI 5527, WD1000/1010 and Xebec S1410 support. Its Xebec support is what makes stock G-DOS 2.4's drives 5 and 6 reachable end-to-end.
- **[CalvaDOS](https://github.com/Egbert-Azure/CalvaDOS)** — sibling project reconstructing Sopp's OMTI hard-disk boot support. **Its documents describe a reconstruction, not the original.** They are a valid source for what that reconstruction does and does not do; they are not evidence about stock G-DOS 2.4 or about Sopp's own code, and should not be cited here as such.

## Open questions

- **Does a reconstructed OMTI boot complete?** Not as of August 2026. A boot sector has been written for `4200h`, and the Sopp EPROM loads and executes it — that part is observed directly and is solid. Beyond that, module loading does not complete. Tracked in CalvaDOS.
- **Does the original `4200h` boot sector contain G-DOS 2.4, or a distinct "Calva-DOS"?** Open. No such artifact has been obtained, and nothing short of recovering one will settle it.
- **Which physical key skips HD boot?** `F1` and `F2` are the candidates; the disassembly notes `F1` may enter the Monitor and `F2` is the likelier force-floppy key. Unresolved.
- **Does a third boot-ROM variant exist** — one that initializes Xebec or WD1000? Unknown; no dump has surfaced.

## Corrections

A dated record of claims that were made here and later withdrawn. Kept because knowing what was believed, and why it was wrong, is part of the evidence.

### Drive count — claimed 2026-08-01, withdrawn 2026-08-07

The stock Xebec driver's parameter table was decoded, correctly, as exposing dispatch slots reached by function codes 5, 6 and 9. That decode was then restated as a claim about the product: that the machine addressed three hard-disk volumes rather than two.

Withdrawn. A structural inference about a dispatch table was allowed to override a period document, which was the wrong call. Three dispatch slots is not the same claim as three configured volumes, and the manual settles the second at two. The decode itself stands and is recorded under "Hard-disk support".

The claim had propagated before it was caught: written into one document, cited by later documents as though it were independent evidence, and eventually used to overwrite a correct manual-sourced statement in a sibling repository. It is the type case for what document-to-document citation does to an unverified claim.

### Harness PASS as evidence of a working boot — claimed 2026-08-01, withdrawn 2026-08-08

Five passages here stated that the Sopp EPROM's hard-disk boot path had been run end to end successfully, on the strength of `run-hdboottest.sh` reaching PASS with 3286+ OMTI operations, zero floppy reads and zero `RECORD NOT FOUND`.

The runs happened and the counts are real. The inference does not follow. The PASS criterion is a *minimum OMTI operation count*, which a boot stuck in a loop satisfies as readily as one that completes; high operation counts and absent floppy reads are consistent with a working boot and equally consistent with a failing one, so they distinguish nothing. The hedge that survived into the original text — that the run was not independently confirmed to reach the interactive command prompt — was the tell.

One part is separable and survives, because it rests on direct observation rather than on the harness: the Sopp EPROM does load and execute a boot sector written for `4200h`. Everything downstream of that is unresolved; see "Open questions".

### Drive-table entry — resolved 2026-08-01

Previously recorded as unidentified, with `PD`/PDRIVE correctly ruled out. Answered: `DRVSEL` itself populates the entry as bookkeeping on every drive select. Both supporting readings are of stock code, so this does not depend on the reconstruction. See "Hard-disk support".

### Citation direction — noted 2026-08-08

Several passages cited CalvaDOS documents as evidence for facts about stock G-DOS 2.4 and about the Sopp EPROM. CalvaDOS is a reconstruction; its output cannot serve as evidence about the original it reconstructs. Claims about stock behaviour now cite the manual, the Grosser reference, or this repo's own disassembly. Claims about the reconstruction cite CalvaDOS and are labelled as such.
