# TCS-Trommeschläger-Genie-IIIs-GDos-2.4

G-DOS 2.4 for the TCS Trommeschläger Genie IIIs, with an emphasis on its native hard-disk support via the Xebec S1410 SASI controller.

## What this repository is about

G-DOS 2.4 is the Genie's own disk operating system, a 1984 TCS product. The Genie IIIs build is the only one that ships hard-disk tooling, and it drives a Xebec S1410 SASI controller: one built-in 10 MB disk, addressed as drives 5 and 6. That is the subject here — what the shipped software does, how it talks to the controller, and how to run it.

This is an archive plus reverse-engineering notes. There is no build system and no test suite.

Two things are deliberately out of scope, because both have their own homes:

- **Booting from hard disk.** Arnulf Sopp's 1986 boot-EPROM modification is a separate program from G-DOS's own driver, and the original boot sector it loads was never recovered. Reconstructing it belongs to [CalvaDOS](https://github.com/Egbert-Azure/TCS-Trommeschlaeger-Genie-IIIs-CalvaDOS). The EPROM dump and its disassembly are held here as artifacts.
- **CP/M**, including Holte's CP/M 3.0 BIOS and its Z-System boot disk, which live in the general [TCS-Trommeschlaeger-Genie-IIIs](https://github.com/Egbert-Azure/TCS-Trommeschlaeger-Genie-IIIs) archive. Klaus Kämpf's CP/M port is relevant here only as corroboration on the controller.

## Sibling repositories

| Repository | Scope |
|---|---|
| [TCS-Trommeschlaeger-Genie-IIIs](https://github.com/Egbert-Azure/TCS-Trommeschlaeger-Genie-IIIs) | General hardware and historical documentation, and all CP/M material — including Holte's CP/M 3.0 BIOS and its Z-System boot disk |
| [TCS-Trommeschlaeger-Genie-IIIs-CalvaDOS](https://github.com/Egbert-Azure/TCS-Trommeschlaeger-Genie-IIIs-CalvaDOS) | Reconstruction of Sopp's 1986 OMTI hard-disk boot support |
| [sdltrs-MultiHDC](https://github.com/Egbert-Azure/sdltrs-MultiHDC) | Emulator with OMTI 5527, WD1000/1010 and Xebec S1410 support |
| [trsextract](https://github.com/Egbert-Azure/trsextract) | Extraction tool for the `.dmk` images here |
| [GenieIIIs](https://github.com/Egbert-Azure/GenieIIIs) (archived) | Original master archive these disks and ROMs came from |

Treat these as one project. Material is placed in whichever repo owns it and linked from the others rather than duplicated.

## G-DOS 2.4

### Origin

`SYS0.SYS` carries `VERSION 2.4  (C) 1984 TCS/MVC`. G-DOS 2.4 is a 1984 product of TCS (Trommeschläger Computersysteme, Sankt Augustin). MVC is **Marcus von Cube**, who wrote it together with **Klaus Kämpf**.

One shared codebase was built into three model-specific system disks — Genie III, IIs, IIIs — via installer job scripts (`GDOSIII.JOB`, `GDOSIIS.JOB`, `GDOSIIIS.JOB`). The disks here span roughly 1984–1985.

### Structure

`GDOS.SYS` is a small boot stub. `SYS0.SYS` is the resident core. `SYS1`–`SYS29.SYS`, plus `OVL2`–`OVL5.SYS` on the IIIs, are individually loaded overlays. `SYS0.SYS` differs between disk instances: all "VERSION 2.4", at different patch levels.

Grosser's *Das DOS-Buch* chapter 3 documents `SYS0/SYS` routine by routine and is the reference to reach for first.

## Hard-disk support

Hard-disk tooling ships only in the Genie IIIs build. It is native support present in the 1985 build, not a later bolt-on — it predates Sopp's boot-EPROM work by a year.

### What the machine shipped as

Per the G-DOS 2.4 manual (*HD-Unterstützung, nur GENIE IIIs*): one built-in **10 MB hard disk**, addressed as **drives 5 and 6** — one physical disk, two volumes. G-DOS 2.4 exposes no user-configurable hard-disk parameters; the geometry is fixed.

The manual is the authority on this and outranks inference. Internal structures in the driver have previously been read as evidence of a different volume count; they are not. Anything describing the stock layout says drives 5 and 6.

The `PD`/PDRIVE command is floppy-only. Confirmed from the physical manual, which shows it configuring floppy drive types, densities and step timing and nothing else — it is not what configures a hard-disk drive-table entry.

### The controller

**Xebec S1410 (SASI).** Both G-DOS 2.4's resident driver and Klaus Kämpf's CP/M port target it.

It is a third protocol, distinct from OMTI 5527 and from WD1000/1010, and getting this right is what unblocked the hard-disk path. Note that the Sopp EPROM's boot-time code drives OMTI instead. The two are separate programs written two years apart against different hardware, and a finding about one says nothing about the other.

The resident driver probes an onboard SASI adapter at ports `00h`–`02h` at boot: the drive ID is written to port `00h` and read back, SEL is pulsed on port `02h`, and BUSY (bit 1) and REQ (bit 0) are polled on port `01h`. *Confidence: moderate-to-high* — this comes from disassembly of the stock driver, matched by working emulation, but no period document in evidence states the port range.

### Geometry

The manual's 10 MB drive is 612 cylinders × 2 heads × 17 sectors = 20,808 sectors. The Sopp EPROM's SET DRIVE CHARACTERISTICS payload declares exactly that, with precomp cylinder 300, which is useful independent corroboration of the drive the machine shipped with.

Two traps worth recording:

- 612 × 2 × 17 and 306 × 4 × 17 give the same total, so agreement on total sectors proves nothing about physical geometry. The EPROM payload encodes the 612-cylinder variant specifically.
- The `.hdv` images in circulation model an **ST225 at 615/4/17, 41,820 sectors** — twice the capacity and a different shape. That is not the period drive.

### Tools

- **`HDFORMAT.CMD`** — erases and two-pass formats the disk, talking to the controller directly rather than through the DOS.
- **`GENDIR.CMD`** — rebuilds the boot directory. Requires a valid drive-table entry for the drive number, via the pointer at `4399h`. *Confidence: high* — Grosser documents `4399h` directly (page 3-31, `47A3h`: `LD (4399),HL`), as the address of the PDRIVE block belonging to the drive just selected.

### What populates the drive-table entry

`DRVSEL` itself, as routine bookkeeping on **every** drive select, for any drive. Not `PD`/PDRIVE, and not `GENDIR.CMD`, which relies on the command interpreter having already selected the drive before it runs.

Grosser documents `DRVSEL` directly (*Das DOS-Buch*, chapter 3, `SYS0/SYS`, pages 3-30 and 3-31, entry at `4776h`). On every select it records the drive number as the current drive at `4308h`, computes its bit pattern into `4309h`, writes the address of that drive's PDRIVE block to the pointer at `4399h`, and copies the block's first eight bytes to `430Ah`–`4311h`. *Confidence: high* — a period source describing stock code, independently matched by a disassembly of the same routine's write set at `4773h`–`47E2h`.

Note the scale this routine actually works at: Grosser's own header gives its input as a drive number 0–3, and PDRIVE blocks exist in RAM only for drives 0–3 (`4371h`–`4398h`). The PDRIVE *sector* on disk carries sixteen-byte entries for drives 0 through 9, which is generic NEWDOS/80 numbering and says nothing about what any particular machine has attached.

### Status

Against `sdltrs-MultiHDC`'s Xebec emulation, stock G-DOS 2.4 reaches its built-in hard disk end-to-end: `PD 5` and `PD 6` return drive data, `HDFORMAT` completes both passes, G-DOS addresses the unit as logical drives 5 and 6, and files written there persist inside the `.hdv` across reboots.

## Running it

Testing is done with [**sdltrs-MultiHDC**](https://github.com/Egbert-Azure/sdltrs-MultiHDC) (`build/sdl2trs`), a fork of SDL2TRS/xtrs.

### Floppy baseline

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

Boots to a working G-DOS 2.4 prompt with the standard banner; `DIR` and other commands behave normally. Use it as the reference point whenever hard-disk behaviour looks wrong.

### Settings-file trap

`sdl2trs` loads `~/.sdltrs.t8c` — a global settings file belonging to no repository — before applying command-line arguments, and an *omitted* flag does not clear a value already stored there. Always pass every `-diskN`/`-hardN`/`-omtiN` slot explicitly, empty string to clear, or you will boot whatever was last attached. `sdl2trs --help` is not a real flag and launches with no overrides at all.

### Tracing

`-diskdebug <hexval>` traces floppy-controller I/O to stdout/stderr — bit 0 `FDCREG`, bit 1 `FDCCMD`, bit 6 `DMK`; see `src/trs_disk.c` in `sdltrs-MultiHDC`. Useful for confirming activity without reading the emulated screen.

## Artifacts held here

### The Sopp EPROM

`ROM/g3s_hd-omti_bootrom_2764.bin` names its own author:

```text
(R)  1984 TCS #8601003
(C)  1984 Uwe Böker
mod. 1986 Arnulf Sopp
```

against the plain `ROM/g3s_8501004_bootrom_2732.bin`:

```text
(R) 1984   TCS
(C) 1984 U.Böker
Reg.Nr.: 8501004
```

The plain ROM is 4 KB (2732); the Sopp ROM is 8 KB (2764), reorganized throughout rather than appended to, with the English boot messages translated to German and an apparent added clock routine. It stays backward-compatible for floppy boot. `src/g3s_hd-omti_bootrom_2764.annotated.md` holds the disassembly.

The ROM's own OMTI boot path, the missing boot sector, and the question of which key skips hard-disk boot are all tracked in [CalvaDOS](https://github.com/Egbert-Azure/TCS-Trommeschlaeger-Genie-IIIs-CalvaDOS), not here.

## Open questions

- **Is there a period source for the SASI adapter port range?** Would upgrade the `00h`–`02h` claim from inference to fact.
- **Does a Xebec-aware boot ROM exist?** No dump has surfaced. Given that the shipped machine's own driver is Xebec, it is a reasonable thing to expect to have existed.
- **What is the actual period drive?** The geometry the software declares is known; the physical model TCS fitted is not confirmed from a document.

## Contents

- `DMK/` — disk images, raw `.dmk`/`.DMK`.
- `ROM/` — ROM and EPROM dumps.
- `src/` — disassemblies and investigation notes.
- `README.md`, `LICENSE` (GPLv3).

Extract disks with `trsextract`: `python3 trsextract.py <image.dmk> -o <dest_dir> -v`. Treat `.dmk` and `.bin` as opaque binaries; `strings -n 4`, `xxd` and `cmp -l` handle quick triage.

## Corrections

Everything above describes stock, shipped software unless marked otherwise. Where a claim rests on a reconstruction rather than on an original artifact, a period document, or this repo's own disassembly, it says so. What follows is a dated record of claims made here and later withdrawn, kept because knowing what was believed, and why it was wrong, is part of the evidence.

**Drive count — claimed 2026-08-01, withdrawn 2026-08-07.** A structural detail internal to the stock driver was restated as a claim about the product: that the machine addressed more hard-disk volumes than it did. Withdrawn. A structural inference was allowed to override a period document. The decode stands; the product claim built on it does not. The claim also propagated before it was caught — written into one document, cited by later documents as though independently evidenced, and eventually used to overwrite a correct manual-sourced statement in a sibling repository.

**Hard-disk boot claimed working — withdrawn 2026-08-08.** Earlier revisions stated that the Sopp EPROM's hard-disk boot path had been run end to end successfully, on the strength of a test harness reaching PASS with a high OMTI operation count and no floppy reads. The runs happened; the inference does not follow. The PASS criterion is a minimum operation count, which a boot stuck in a loop satisfies as readily as one that completes. Those numbers are equally consistent with success and failure and therefore distinguish nothing. Hard-disk boot status now lives in CalvaDOS, where the work is.

**Citation direction — noted 2026-08-08.** Several passages cited CalvaDOS documents as evidence for facts about stock G-DOS 2.4 and about the Sopp EPROM. CalvaDOS is a reconstruction; its output cannot serve as evidence about the original it reconstructs. Claims about stock behaviour now cite the manual, Grosser, or this repo's own disassembly.
