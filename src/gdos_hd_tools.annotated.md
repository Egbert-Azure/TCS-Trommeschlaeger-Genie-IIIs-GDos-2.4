# Annotated notes — `HDFORMAT.CMD` and `GENDIR.CMD` (GDOS 2.4, Genie IIIs build)

Both from `DMK/g3s-gdos24_extract/`. Disassembled via `sdltrsOMTI`'s `zbx` debugger's `cmd <file>` loader (it parses the GDOS/CMD file format correctly and reports the real entry point/load address - do not hand-parse the header as a plain TRS-80 SYSTEM-tape block format, it isn't one), then `dis <addr>,<addr>`. Read-only against `sdltrsOMTI`, nothing written there.

## `HDFORMAT.CMD` — loads at `7000h`, entry `7000h`

```
7000h  print string @708Dh: "Wollen Sie die HARDDISK tatsächlich löschen? "
700Bh  read up to 4 chars into 4200h-4203h (system call at 0040h)
700Eh  HL = (4200h) ; uppercase both bytes (RES 5,H / RES 5,L)
7015h  compare HL against the 2 bytes at 414Ah via RST 18h
7019h  JP NZ,4030h   ; *** no match -> silently abort, no further output ***
701Ch  A = (4202h)  ; the THIRD character typed
701Fh  CP 32h ('2') ; JP Z,704Bh
       -> not '2': format branch with L=05h, fill byte E5h  (7024h-7048h)
       -> is '2'  : format branch with L=13h, fill byte 6Ch (704Bh-7072h)
7072h  JP 402Dh (return to DOS)
```

**The confirmation word is "JA"** (German "yes" - `414Ah` holds bytes `4Ah 41h` = `'J','A'`), not "J" or "Y". Typing anything else matches nothing, hits the silent `JP NZ,4030h` abort, and produces no further screen output - this is almost certainly why an earlier attempt looked like "nothing happened."

The third typed character then picks between two hardcoded branches with different parameters (drive-select bit patterns / fill bytes) - this reads as **"which physical Winchester unit" (default = unit 1, `'2'` = unit 2 on the SASI bus)**, not a GDOS logical drive number. `HDFORMAT.CMD` talks directly to the hard-disk controller and does **not** touch GDOS's drive/PDrive table at all - no PDRIVE setup should be needed before running it, only a physically-attached OMTI drive.

**Confirmed from the real manual**: the Genie IIIs' built-in 10MB hard disk is addressed as GDOS **drive numbers 5 and 6**. This almost certainly maps directly onto the unit-1/unit-2 split above - drive 5 = unit 1 (default), drive 6 = unit 2 (`'2'` typed as the third character).

## `GENDIR.CMD` — loads at `5200h`, entry `5200h`

```
5200h  CALL 4CD5h ; JR NZ,520Ah  else (Z, no args at all) print error 2Fh, JP 4409h (DOS error handler)
520Ah  skip an optional leading ':'
5210h  read one digit char, AND 0Fh (ASCII->value), CALL 445Eh (validate?), JR NZ,5207h on failure
        *** takes a drive-number argument: "GENDIR :N" or "GENDIR N" ***
5219h  optional second argument: an 8-char NAME (uppercase A-Z, copied into a buffer at 54DCh),
       terminated by CR/comma/space
526Dh  CALL 4CD5h ; JR NZ,5207h
5272h  IX = (4399h)              ; *** a fixed system pointer - almost certainly GDOS's
                                     resident drive/PDrive table base ***
5279h  CALL 544Ah (index into the table using the parsed drive number, via DE)
527Fh-52DDh  read/compare fields at (IX+00h), (IX+01h), (IX+05h), (IX+08h) and a staging
             area at 4200h/4202h/421Fh against expected values/templates at 5491h/547Fh
             (CALL 5441h, a block-compare) - mismatches fall through to 52DFh
```

This is where `Schlechte PDrive-Daten` ("bad PDrive data") almost certainly fires: `GENDIR.CMD` expects the drive-table entry (indexed via `4399h`) for the drive number you give it - now known to be `5` or `6` - to already contain valid/expected data before it will build `BOOT/SYS`+`GDOS/SYS`+`INHALT/SYS` on that drive. **Not yet found: what command actually populates that table entry for a hard disk** - none of `PDRIVE.CMD`/`ID.CMD`/`IDENT.CMD`/`DDSD.CMD` are it (all three are floppy density/track-count auto-detect tools per their own strings, ported from NEWDOS-80's `DDSD.CMD`, and `PD`/PDRIVE itself is confirmed 100% floppy-only from the real manual). It may be a DOS-resident command (not a separate `/CMD` file) rather than something visible in the file listing.

## Practical upshot for testing

1. `HDFORMAT.CMD`, answered with **`JA`**, should work directly against an attached (blank) OMTI drive with no GDOS-side drive setup at all - try this first.
2. `GENDIR.CMD :5` (or `:6`) is the next step after formatting, and needs the `4399h`-indexed table entry for that drive to already be valid - what populates that entry is still unidentified.

### `PD 5`/`PD 6` also fail with `Bauteil nicht erreichbar` — not OMTI-vs-WD1000-specific

Empirically tested both attachment points with the standard (non-Sopp) boot ROM, `HDV/g3s-gdos24-omti-10mb.hdv` correctly attached in both cases (confirmed via clean boot logs, zero errors):

- `-omti0`: `PD 0` shows the floppy table fine (drives 0-3 starred/active, matching the booted floppies); drives 5/6 unstarred, not queried directly this round.
- `-hard0` (WD1000/1010): same `PD 0` floppy table (only 0-3 starred). Typing **`PD 5` directly returns `Bauteil nicht erreichbar`** — a live hardware probe, not just a static table lookup, and it fails identically to `HDFORMAT.CMD`'s own failure.

**Conclusion: this isn't an OMTI-vs-WD1000 question.** Neither controller is reachable from GDOS when booted via the standard ROM, regardless of which one the disk is attached to. The `*` (active) marker in `PD`'s table only appears on drives whose controller was actually initialized by the *boot ROM* at startup (floppy 0-3, via the standard ROM's own floppy-controller init) - and since only the **Sopp ROM** ever touches hard-disk-controller ports at boot (confirmed via `-io` tracing: zero OMTI/WD1000 I/O with the standard ROM, on any boot), the working theory is that **GDOS itself never initializes the hard-disk controller - it only probes/uses it, and expects the boot ROM to have already brought it up.** If true, reaching a "drive 5/6 connected" state at all requires booting via the Sopp ROM, which is exactly the path that hits the `sdltrsOMTI` crash characterized in `src/omti_boot_crash_investigation.md`. Not yet confirmed: whether `PD 5`/`HDFORMAT` might succeed if tried *immediately* after a Sopp-ROM boot reaches its floppy-fallback GDOS prompt (which is reachable, per that doc), before whatever later interaction triggers the crash.
