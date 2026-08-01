# Investigation: `sdltrsOMTI` crash during Sopp-EPROM HD-boot-fail fallback

*Updated 2026-07-20, end of second session — **root cause found, investigation closed for now.** Read this whole file before touching code or disk images again.*

**Correction, 2026-08-01, from the sibling project `CalvaDos`. Kept as a
note here, not a rewrite — the investigation below stays as it was written.**
Two claims in the root-cause section need qualifying, and one needs a
caveat stated plainly rather than left implicit:

- **"The controller is really Xebec, not OMTI" is correct for GDOS 2.4's own
  resident driver, and reads too generally as written.** The Sopp EPROM's
  *own boot-time* code — the detect-and-load logic this document is actually
  about, running before GDOS is loaded at all — genuinely drives OMTI, not
  Xebec: confirmed by this repo's own port table in
  `g3s_hd-omti_bootrom_2764.annotated.md` ("ports `40h`-`43h` match
  `sdltrs-MultiHDC`'s documented OMTI 5527 register range exactly") and now
  by `CalvaDos`'s working OMTI driver and OMTI-driven boot,
  `run-hdboottest.sh` reaching PASS. Both controllers are real; they belong
  to different software.
- **"GDOS 2.4 has no configurable hard-disk parameters at all... fixed
  10MB, two-partition layout (matches drives 5/6)" undercounts the driver's
  own addressing.** `CalvaDos`'s extraction of the *stock* Xebec driver
  blob decodes a third hard-disk dispatch slot, drive `9`, in the parameter
  table itself — see `CalvaDos/src/hd-driver/abi.md`. The "fixed 10MB,
  two-partition" description most plausibly describes the specific shipped
  product, not a limit in the driver code.
- **One caveat this repo's own success does not settle, stated honestly:**
  the `PC=002Bh` crash chased throughout this document happened in the
  EPROM's *fallback-to-floppy* path — reached only because the attached
  disk had no valid boot sector to jump to (see "The blocker," below).
  `CalvaDos` has never tested that specific scenario; its own testing
  always has a valid boot sector present at `4200h`, so its success
  confirms the EPROM's *success* path works against OMTI, not that this
  specific crash (in the *failure* path) was, or wasn't, a genuine bug —
  independent of the Xebec-vs-OMTI question above, which concerns the
  protocol, not this particular fallback-path crash.

## ROOT CAUSE (found by the user, closes out this investigation)

**GDOS 2.4 and Klaus Kaempf's CP/M port for the TCS Genie IIIs both use the SASI protocol of the Xebec S1410 controller** (source: [Xebec S1410A Owner's Manual](https://dn720005.ca.archive.org/0/items/xebec-s-1410-a-owner-manual/Xebec%20S1410A%20Owner%20Manual_text.pdf)). Xebec S1410 SASI is **not compatible with WD1000/1010, and not compatible with OMTI 5527 either** — "somewhat more similar" to OMTI than to WD1000, but still a distinct protocol. `sdltrsOMTI` emulates exactly two controllers, OMTI 5527 and WD1000/1010 — **neither is the one this hardware/software combination actually needs.**

This retroactively explains every result in this document:

- **WD1000 (`-hard0`) never worked** (`Bauteil nicht erreichbar` for `PD 5`, even with a natively-generated `.hdv`): wrong protocol family entirely, not a formatting or ROM issue.
- **OMTI (`-omti0`) got much further** — genuinely detected, completed a real SASI command exchange, transferred 512 bytes correctly, reported success correctly — because OMTI is "somewhat more similar" to Xebec S1410 than WD1000 is. But it's still not the same protocol, so somewhere in that similar-but-not-identical command/status exchange, the ROM's Xebec-specific expectations and the emulator's genuine OMTI 5527 behavior diverge just enough to corrupt state — very plausibly *this*, not a Z80-core or `trs_memory.c` bug, is what's actually behind the `PC=002Bh` crash chased at length below. Not re-verified against this new theory line-by-line, but it's a far better-supported explanation than anything in the "leading theory" section.
- **`PD 5`/`HDFORMAT` never becoming "reachable" under the standard ROM, regardless of `-hard0` vs `-omti0`**: consistent — GDOS's own hardcoded expectations are for Xebec S1410 responses specifically; nothing this fork emulates satisfies them.
- **The "third boot ROM variant" theory is moot**: there's no missing *ROM* to find — the missing piece is Xebec S1410 *controller emulation* in `sdltrsOMTI` itself.
- **Also confirmed by the user**: GDOS 2.4 has **no configurable hard-disk parameters at all** — it's hardcoded to a fixed 10MB, two-partition layout (matches drives 5/6 from the manual). This likely also explains why no "connect the hard disk" GDOS command was ever found (open question elsewhere in this repo's docs) — there may not be one; the fixed Xebec-specific hardware either responds correctly at a hardcoded protocol level or it doesn't, with no user-facing configuration step in between.

**What it would actually take to move forward**: real Xebec S1410 SASI protocol emulation added to `sdltrsOMTI` (a genuine coding project in that fork, out of scope for this repo — which is read-only against it — and not something to attempt via more testing/retries from this side). Until/unless that exists, GDOS 2.4's hard-disk path cannot be exercised end-to-end in this emulator, by any ROM, controller-attachment point, or hotkey combination. Everything below this point is the historical record of how that conclusion was reached — kept for reference, not as a to-do list to keep pulling on.

## The goal

Boot GDOS 2.4 (`DMK/G3S-GDOS24.DMK`) under the Sopp OMTI EPROM (`ROM/g3s_hd-omti_bootrom_2764.bin`) with a real OMTI hard disk attached, reach a live GDOS prompt where the hard disk is actually *reachable* (not just attached), and run `HDFORMAT.CMD`/`GENDIR.CMD` against it. GDOS addresses the built-in 10MB hard disk as **drive numbers 5 and 6** (confirmed from the real manual — see `README.md`).

## The blocker: a reproducible crash, not a GDOS or ROM problem

With a blank OMTI `.hdv` attached (`HDV/g3s-gdos24-omti-10mb.hdv` — 306 cyl/4 heads/17 sec, the manual-confirmed real geometry; built by `src/build_blank_omti_hdv.py`), the Sopp ROM correctly detects the OMTI controller, issues a real SASI READ, correctly reads back 512 bytes of (all-zero, since the disk is blank) sector data, correctly determines the read "succeeded" (no error bit set), and is about to cleanly `RET` out of its detection routine (address `1174h` in the ROM — see `g3s_hd-omti_bootrom_2764.annotated.md`) to fall back to floppy boot (since a blank disk has no valid boot sector to jump to).

**That `RET` doesn't return correctly.** Instead of landing at `1139h` (the real return address, per the `CALL 1144h` at `1136h`), the Z80 program counter ends up at `002Bh` — the second byte of an unrelated `LD BC,03EFh` instruction in the ROM's own startup relocation code. From there, the CPU decodes garbage bytes as an endless stream of writes to the *floppy* controller's ports (`0xE0-0xE3`/`0xEC-0xEF` on this hardware — `select_write`, `command_write`, `sector_write`, `track_write`), each one tripping `sdltrsOMTI`'s `trs_disk_command(0x2B) not implemented - bogus drive select` error, forever. The screen shows garbage; the process doesn't crash outright, it just spins.

**Reproducibility is not fully settled.** Most attempts hit the crash very quickly (often before any user interaction at all, sometimes even automatically during boot itself). But at least one boot this session (the one where a keystroke-injection attempt failed silently before any key was sent — see below) reportedly reached a **working, usable GDOS DOS prompt** that stayed up long enough for the user to be "on the DOS prompt" before it eventually went to garbage. This was not captured in a saved log, so it's not independently confirmed from a trace — but if real, it means **there may be a genuine usable window at the prompt before whatever triggers the crash catches up**, rather than the crash being instantaneous. This is the single most important loose end to resolve next session — see "Open question" below.

**Never happens** with: the plain ROM (no OMTI code at all), or the Sopp ROM with nothing attached to `-omti0`/`-hard0` (the presence probe fails immediately, taking a much shorter path to the same eventual floppy fallback).

**Not an OMTI-vs-WD1000 issue.** Tested attaching the same disk via `-hard0` (WD1000/1010, "Xebec-style") with the *standard* (non-Sopp) ROM instead: boots clean, but `PD 5` (a live hardware probe, not just a table lookup) fails identically with `Bauteil nicht erreichbar`. So GDOS itself never initializes either hard-disk controller — it only probes/uses one, and apparently expects the boot ROM to have already brought it up. Since only the Sopp ROM ever touches hard-disk-controller ports at boot (confirmed via `-io` tracing: zero I/O to either controller with the standard ROM, regardless of what's attached), reaching a "drive 5/6 connected" state at all appears to require booting via the Sopp ROM specifically — which is exactly the path that hits this crash.

## What's been ruled out, with evidence (don't re-litigate these)

Investigated by reading `sdltrsOMTI`'s actual source (`~/Documents/GitHub/sdltrsOMTI`, read-only — nothing was written there) and cross-referencing line-by-line against the traced ROM disassembly and the live `-diskdebug 0x3 -io 0xc` trace log.

1. **Not GDOS.** This crash happens entirely within the boot ROM's own hard-disk-detect routine, before GDOS is ever loaded from the floppy.
2. **Not the ROM's own logic.** Traced every instruction from the OMTI presence probe (`1108h`) through the final status-byte read (`116Ch`) and the `RET` (`1174h`). The ROM asks for exactly what it should and correctly interprets what it gets back.
3. **Not `trs_omti.c`'s SASI/OMTI state machine.** Cross-referenced the live trace against `omti_command()`/`omti_data_in()`/`omti_finish()` line by line: the 512-byte transfer is byte-for-byte correct, the phase transitions to `OMTI_PH_STATUS` exactly on the 512th byte, `final_status` correctly reports success (`0x00`), and the ROM correctly reads it. This code is doing exactly what it's supposed to.
4. **Not a port-number collision in `trs_io.c`.** There's a second, unrelated meaning for ports `0x41-0x43` in that file (an "X-MEM/80" memory-bank feature) — but it's gated under a completely separate `switch (trs_clones.model)` branch (`default:`, i.e. *not* `GENIE3S`) and additionally behind an `if (xmem80)` check. No real collision for our config.
5. **Not the floppy motor-timeout NMI.** `trs_interrupt.c`'s `trs_disk_motoroff_interrupt()` explicitly does nothing when `trs_model == 1` (`/* no such interrupt */`) — and every test here launched with `-model 1`. Confirmed by reading the code, not inferred.
6. **Probably not a regular maskable interrupt either.** The ROM's very first instruction is `DI`. The only `EI` found anywhere in the traced ROM code sits in what looks like a DOS system-call jump table (`014F-017F`) that our actual execution path never calls into.

## Leading theory (unconfirmed)

Given 1-6 above, the remaining plausible culprits are lower-level than anything OMTI-specific:

- A Z80 core emulation bug in how `INI`/`OTIR` (used heavily in the ROM's byte-at-a-time SASI transfer loop) affect flags/timing in `z80.c`, exposed only by this unusually long, tight, real-hardware-accurate loop (512 individual `CALL`+`INI` round trips) — nothing else in normal TRS-80/Genie software does this.
- Something in `trs_memory.c`'s bank-switching interacting badly with the specific sequence of `OUT (FAh)`/`OUT (D6h)`/`OUT (D7h)` bank-control writes this ROM does around the OMTI sequence (these ports are Genie-IIIs-specific bank control, not touched by the `trs_omti.c` code itself but very much active in the surrounding ROM code — not yet checked).

Neither has been confirmed. Both would require actually single-stepping through the crash (watching `SP` and the stack contents instruction-by-instruction right up to the bad `RET`) rather than reasoning from static disassembly + log correlation, which is as far as the methods used so far can go.

## The hotkey: fully identified, but not yet successfully triggered

The ROM's hotkey check (see `g3s_hd-omti_bootrom_2764.annotated.md`) tests bits 0-1 of a keyboard-matrix byte at `38A0h`. Read `sdltrsOMTI`'s own keyboard source (`src/trs_sdl_keyboard.c` line 817-820, `src/trs_sdl_interface.c` line 1417-1426) to get the exact mechanism:

- Address `38A0h` reads `keystate[8]`, which for `GENIE3S`/`EG3200` clone models represents **F1-F8**, one bit each (bit 0 = F1, bit 1 = F2, ... bit 7 = F8).
- For `case GENIE3S`, host `SDLK_F1`-`SDLK_F8` map directly: `keysym.sym = (keysym.sym - SDLK_F1) + 0x080`, landing exactly on this row. So **F1 (or F2) is confirmed correct** — not a mapping guess.
- Practical problem: on macOS, plain F1/F2 are OS-level brightness shortcuts. Holding `fn+F1` physically is awkward and the brightness OSD can steal window focus mid-hold.
- Tried simulating the keystroke via `osascript`/System Events (`key code 122`=F1, `key code 120`=F2) **six** different ways across two sessions: delayed keydown, near-zero-delay keydown, pre-holding before the process even launched, with `-keystretch 200000` for extra tolerance, and finally clean isolated tests of F1 alone and F2 alone (2.5s hold each, Accessibility permission confirmed granted and working — `osascript`'s own frontmost-window check succeeded every time). **All six failed identically** — every corresponding log shows full OMTI activity starting at line 1, i.e. the hotkey flag was never set in time, for both candidate keys equally. This rules out "wrong key" as the explanation (F1 and F2 fail exactly the same way) and confirms it's purely a timing race: the ROM's keyboard read happens within the first handful of instructions after `DI`/`SP` setup, likely well under 100ms of real wall-clock time after the window is created, and `osascript`'s own per-call process-spawn overhead alone is plausibly enough to lose that race every time regardless of target key. **Root cause found, and it's not timing at all: `osascript`/System Events synthetic keystrokes don't reach this SDL2 app's keyboard input, period — confirmed with zero timing pressure.** After ruling out "wrong key" (F1 and F2 both fail identically) and "Sopp ROM complexity" (F1 fails identically against the plain standard ROM too, with no OMTI/HD involved at all), the real test: booted normally, let GDOS settle at a live DOS prompt for 4+ full seconds (no timing pressure whatsoever), then sent plain letter keys (`keystroke "DIR"`) via the same `osascript`/System Events mechanism. **Nothing appeared on screen at all.** So every attempt this session was doomed regardless of timing — `osascript`'s synthetic events (even with Accessibility permission correctly granted and `set frontmost` succeeding) simply never reach this SDL2 app's actual keyboard handling. SDL2 apps commonly read keyboard input through a lower-level path (raw HID/IOKit-style) than the standard Accessibility/CGEvent queue `osascript` posts to, which would fully explain a 100%-consistent, non-timing-dependent failure like this.

**Conclusion: abandon `osascript`/System-Events-based key injection for this app entirely** — it's not a matter of tuning delay/keystretch, the mechanism doesn't work at all. Two remaining paths for automated or assisted input: (1) a tool that posts genuinely lower-level HID events (not `osascript`) — unexplored this session; (2) the user physically holding the real key, ideally with the macOS Function-Keys system setting enabled first so plain F1/F2 aren't intercepted as brightness shortcuts (never actually tried — only the raw `fn+F1` physical route was attempted, which has the brightness-OSD-steals-focus problem noted above). Otherwise, the "usable window" angle below doesn't need any keystroke automation at all and remains the best next-session starting point.

## Open question: is there a usable window at the prompt before the crash?

Not confirmed, but plausible and important. If the crash isn't instantaneous — if GDOS can actually be typed at for some real amount of time after a normal (non-hotkey) Sopp-ROM+OMTI boot reaches its floppy fallback — then the practical path to testing `HDFORMAT.CMD`/`PD 5` doesn't need the hotkey or a `sdltrsOMTI` fix at all: just boot normally and race to type before whatever triggers the crash catches up. **Next session, first thing to do**: boot cleanly (`boot_gdos24_omti.command`, no automation), and the moment the GDOS prompt appears, immediately try `PD 5` and/or `HDFORMAT` (answer `JA`). Note whether it works, how long the window lasts (rough seconds), and whether it's the same every time or variable.

## New lead: a third boot ROM variant may exist (WD1000/Xebec-initializing)

The user found a hint that **both** hard-disk controller standards (Xebec/WD1000-class and OMTI) were genuinely offered on real Genie IIIs hardware, not just OMTI as Sopp's later addition. That reframes the earlier WD1000 test (see above — `PD 5` failed identically via `-hard0` with the *standard* 2732 ROM): it doesn't rule out WD1000 support in general, only that *this specific ROM* doesn't initialize it, exactly as it doesn't initialize OMTI either. Just as the Sopp ROM is the one that initializes OMTI at boot, there may be a **third, not-yet-found boot ROM variant that initializes WD1000/Xebec at boot** — worth a targeted search through `~/Documents/GitHub/GenieIIIs/rom/` (and its `DMK`/other subfolders) for anything WD1000/Xebec-flavored that isn't the plain `g3s_8501004_bootrom_2732.bin` or the OMTI `g3s_hd-omti_bootrom_2764.bin`. If found, it'd be worth testing the same way (`-hard0` + this new ROM) — and being a different, independent codebase from the Sopp/OMTI ROM, it may not share the `PC=002B` crash at all.

**Confirmed not a disk-image-formatting issue**: the user also generated a fresh 10MB `.hdv` using `sdltrs`'s own native hard-disk-creation function (GUI-based, guaranteed correctly formatted for whichever controller convention it targets, independent of `src/build_blank_omti_hdv.py`) and tried it with the standard 2732 ROM — same failure, no success. So the standard ROM's inability to reach drive 5/6 isn't about a subtle header/geometry mismatch in our own script; that ROM genuinely never touches hard-disk-controller ports at all, regardless of image format. Strengthens the case for the "third ROM variant" theory above being the real gap, not the disk image.

## Status: closed pending real Xebec S1410 emulation

Per the root-cause section at the top, none of the workarounds explored in this document (hotkeys, controller-switching, ROM-hunting, keystroke automation, the built-in `hdboot` WD1000 patch) can succeed, because the actual gap is a missing controller protocol in `sdltrsOMTI`, not anything fixable from this repo's side.

**New sibling repo created: `~/Documents/GitHub/sdltrsXebec`** — a fresh clone of `sdltrsOMTI` (full history preserved, `origin` renamed to `sdltrsomti-upstream` so nothing pushes back to the original project; confirmed builds clean as of creation), meant to add Xebec S1410 SASI emulation — the third controller protocol this hardware/software combination actually needs. Not a modification to the existing `sdltrsOMTI` checkout (still strictly read-only from *this* repo). See that repo's own `README.md` for architecture/status — as of this writeup, no Xebec-specific code has been written yet, just the fork itself. Primary protocol reference: the [Xebec S1410A Owner's Manual](https://dn720005.ca.archive.org/0/items/xebec-s-1410-a-owner-manual/Xebec%20S1410A%20Owner%20Manual_text.pdf). Once Xebec emulation works there: come back here, boot with the Sopp ROM + a Xebec-emulated drive attached, confirm `PD 5` shows reachable, then `HDFORMAT.CMD` (answer `JA`), then `GENDIR :5`/`:6` — noting `GENDIR.CMD` will still need GDOS's drive-table entry (pointer at `4399h`) for drive 5/6 to be valid first, and **what populates that entry is still unidentified** (confirmed not `PD`/PDRIVE, not `PDRIVE.CMD`/`ID.CMD`/`IDENT.CMD`/`DDSD.CMD` — and per the root-cause note above, may not be a user-facing command at all).

## Reference: how to reproduce

```sh
cd ~/Documents/GitHub/sdltrsOMTI
./build/sdl2trs -model 1 \
  -rom "<this-repo>/ROM/g3s_hd-omti_bootrom_2764.bin" \
  -disk0 "<this-repo>/DMK/G3S-GDOS24.DMK" \
  -disk1 "" -disk2 "" -disk3 "" -disk4 "" -disk5 "" -disk6 "" -disk7 "" \
  -hard0 "" -hard1 "" -hard2 "" -hard3 "" \
  -omti0 "<this-repo>/HDV/g3s-gdos24-omti-10mb.hdv" -omti1 "" \
  -diskdebug 0x3 -io 0xc -nofullscreen
```

(Or just run `boot_gdos24_omti.command` in this repo's root, which does exactly this and logs to `logs/`.) Crash shows up, when it does, as `trs_disk_command(0x2B) not implemented - bogus drive select` repeating forever in the log, and garbage on screen.
