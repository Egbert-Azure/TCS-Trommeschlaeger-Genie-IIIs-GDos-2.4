# Annotated disassembly — `ROM/g3s_hd-omti_bootrom_2764.bin` (the Sopp EPROM)

Arnulf Sopp's 1986 hard-disk-boot modification of the standard 1984 TCS/Uwe Böker Genie IIIs boot ROM (see `README.md` for the string-level identification). 8192 bytes, mapped at Z80 addresses `0000h`-`1FFFh` (confirmed via `sdltrsOMTI`'s memory map: `address < trs_rom_size` reads directly from `rom[address]`).

Method: static disassembly via `sdltrsOMTI`'s built-in `zbx` debugger (`dis 0,0x1fff`, read-only, no ROM/disk attached — `~/Documents/GitHub/sdltrsOMTI` was never written to). Full raw output: `g3s_hd-omti_bootrom_2764.raw_disasm.txt` (linear/blind — includes data misdecoded as instructions outside the traced flow below). This file covers only the portion of the ROM whose control flow has actually been traced and confirmed; large parts of the 8KB (helper subroutines beyond the ones listed, data tables, the banner text bytes, the exact floppy-fallback path body) are **not yet analyzed** — see "Not yet traced" at the end.

I/O ports referenced (from this trace only):

| Port | Direction | Role (as observed here) |
|---|---|---|
| `F9h` | in/out | system/video wait-state or bank-control handshake |
| `FAh` | out | bank/mode select (values `10h`, `20h`(? unconfirmed), `55h`, `90h`, `D4h`, `E4h` seen) |
| `D6h`, `D7h` | out | further bank/mode control (`0Fh` then `00h` written to both early in boot) |
| `F6h` | out | used in an `outi`-driven block-out loop at `01A5h` |
| `40h` | in | OMTI data/status |
| `41h` | in/out | OMTI status / control |
| `42h` | in | OMTI status (the presence probe reads this) |
| `43h` | out | OMTI control | 

`40h`-`43h` match `sdltrsOMTI`'s documented OMTI 5527 register range exactly (its own `README.md`: "ports 0x40-0x43"), confirming this ROM is genuinely talking to the same controller that fork emulates.

## Boot flow, as traced

```
0000h  DI; SP=3C00h
       wait-loop on port F9h until it reads back 20h
       OUT (D6h),0Fh ; OUT (D7h),0Fh ; OUT (D6h),00h ; OUT (D7h),00h   ; bank/mode setup

0019h  A = (38A0h)              ; *** read ONE byte of the keyboard matrix ***
001Ch  (FFFFh) = A              ; stash it - this is the hotkey state for the whole boot

001Fh  OUT (FAh),10h
0023h  relocate ROM[019Eh..058Ch] (0x3EF bytes) -> RAM 3800h..3BEEh
002Eh  JP 3800h                  ; run the relocated copy

       ; (relocated code, not yet independently re-disassembled at its RAM location -
       ;  reconstructed here from where it jumps back INTO the ROM)
  ...  JP 0031h                  ; back into ROM

0031h  CALL 0185h                ; draw a banner: clear 3C00h-3FFEh to spaces (video RAM),
                                  ; then copy 0xC0 bytes of banner text from ROM 058Dh to 3C00h
0034h  relocate ROM[0068h..014Eh] (0xE7 bytes) -> RAM 3800h (overwrites the earlier copy)
003Fh  JP 1100h                  ; -> OMTI hard-disk detect/init

; ---- OMTI hard-disk detect (1100h) ----
1100h  A = (FFFFh); AND 03h; JP NZ,3800h     ; hotkey-flag bits 0-1 set => ABORT to floppy path
1108h  IN A,(42h); CP FAh; JR NZ,1105h        ; poll OMTI status port 42h for FAh ("controller present")
110Eh  OUT (41h),0 ; OUT (43h),0              ; clear OMTI control regs
       D = 20h (32 retries), HL = 11BCh (CDB template), BC = 0500h
1115h  CALL 1175h ; CALL 1185h                ; send a SASI command (6-byte CDB, phase-driven -
                                               ;  matches sdltrsOMTI's documented OMTI_PH_CDB clocking)
1123h  IN A,(40h); RES 5,A; OR A; JR Z,1133h
       (nonzero) CALL 11DCh; DEC D; JR NZ,1115h   ; retry up to 32x
       (exhausted) JP 3800h                        ; give up -> floppy path
1133h  CALL 1191h ; CALL 1144h ; JR NZ,1105h        ; second command + a data-phase read (1144h does
                                                      ; an INI block-input from the OMTI data port -
                                                      ; this looks like an actual sector-read/verify,
                                                      ; not just a status ping)
113Bh  E = 01h                    ; *** E = boot-device selector, 1 = hard disk ***
113Dh  IX = 4200h                 ; *** hard-disk boot-sector load address ***
1141h  JP 382Eh                   ; back into the (by-now-twice-relocated) RAM code

; ---- boot-sector load, reached from the 1157h helper (part of the 1144h call above) ----
1157h  HL = 4200h ; BC = 0040h ; D = 02h
115Fh  CALL 1185h ; INI            ; block-input 0x40 bytes from the OMTI data port straight into
                                    ; RAM at 4200h - i.e. the ROM has the controller stream a sector
                                    ; of real data directly into 4200h. This is the hard-disk boot
                                    ; sector being loaded, MBR-style.

; ---- device dispatch (0079h), reached via the RAM code after JP 382Eh / the floppy-abort paths ----
0068h  A = D4h; OUT (FAh),A; XOR A; (3894h) = 0
0070h  A = (FFFFh); RRCA; JR C,00C8h    ; hotkey-flag bit 0 (via rotate) => 00C8h: OUT(FAh),90h; JP 0056h
                                          ; i.e. **this exact bit is a manual floppy-boot override -
                                          ; the "hotkey" the investigation was looking for.**
0076h  CALL 3867h
0079h  IX = 0000h
       A = E; CP 03h; JR Z,008Eh         ; E==3 -> keep IX=0000h
       IX = FC00h
       CP 02h; JR Z,008Eh                ; E==2 -> keep IX=FC00h
       IX = 4200h                        ; else (E==1, hard-disk path) -> IX=4200h
008Eh  ... push IX; further per-device init (clear 0x36 bytes at 4000h, clear 0x27 bytes after DE,
       then more flag-dependent jumps back to 0042h/0056h) ...

; ---- hotkey compare (0042h) - a second, independent test of the same flag byte ----
0042h  A = (FFFFh); CP B2h; JR NZ,0052h
0049h  (match: B2h) XOR A; OUT(F9h),A; A=E4h; OUT(FAh),A; JP (IX)   ; dispatch to the selected boot device
0052h  (no match) A = 55h; JR 0057h
0056h  (floppy-abort target) XOR A
0057h  (FFFFh) = A; relocate ROM[064Dh..] (0x871 bytes) -> RAM F700h; JP F700h  ; (floppy-path body -
                                                                                   ; not yet traced)
```

## What this establishes (confirmed, not speculative)

- **There is a genuine hotkey mechanism.** A single byte of the keyboard matrix (address `38A0h`, one specific row) is read once, right at the very start of boot, latched at `FFFFh`, and consulted repeatedly afterward (`AND 03h` at `1100h`, `RRCA`/carry-bit test at `0070h`, exact `CP B2h` at `0042h`) to decide whether to even attempt hard-disk boot at all, or fall straight through to the floppy path.
- **`E` is an explicit boot-device selector**, set to `1` only on confirmed OMTI success (`113Bh`), and used at `0079h`-`008Ah` to choose `IX`: `E=1 -> IX=4200h`, `E=2 -> IX=FC00h`, `E=3 -> IX=0000h`. **Now fully identified** via real TCS documentation of the *standard* (non-Sopp) init loader — see `genie3s_init_loader.md`: this is the base loader's own disk-type dispatch (byte at offset `E0h` of track0/sector0: `01`=G-DOS floppy→`4200h`, `02`=CP/M floppy→`FC00h`, `03`=service disk→`0000h`). The Sopp OMTI extension reuses this exact same `E`/`IX` convention for its own HD-boot success case (`E=1`/`IX=4200h`) rather than inventing a new one — `4200h` is simply the fixed landing address for "real GDOS bootstrap code" regardless of whether it came from a floppy's own boot sector (base loader's job) or an OMTI hard disk's boot sector (Sopp's extension).
- **The hard-disk path is a classic two-stage bootstrap.** The ROM only probes the OMTI controller, confirms it's present and responds to a real data-phase command (`1144h`'s `INI` loop), then has the controller stream one sector (0x40... bytes read via `INI`, so actually 64 bytes per `INI` call — the CDB at `1191h`/`1144h` likely requests more than one 64-byte block; not yet fully counted) directly into RAM at `4200h` and jumps there (`IX=4200h` then dispatched via `JP (IX)` at `0049h`). **The ROM does not contain GDOS or Calva-DOS itself** — it hands off to whatever bootstrap code the hard disk's own first sector(s) contain. That on-disk boot-sector code is a separate, not-yet-obtained artifact.
- **Everything here talks to the OMTI controller on ports `40h`-`43h`**, matching `sdltrsOMTI`'s existing OMTI emulation exactly, confirming both that this fork's port mapping is correct for this ROM and that testing the HD-boot path against it (once a correctly-formatted OMTI `.hdv` boot sector exists) is viable.

## Correction: the hotkey may not do what several test attempts assumed

Per the real base-loader documentation (`genie3s_init_loader.md`), the *standard* loader's own keyboard checks are **`F8` = reload character set** (power-on only) and **`F1` = enter the Monitor** — neither is "skip hard-disk boot, force floppy," because the base loader predates hard-disk support and doesn't know OMTI exists. If the Sopp ROM's `38A0h`/`AND 03h` check (bits 0-1 = `F1`/`F2` per `keystate[8]`, confirmed via `sdltrsOMTI`'s own keyboard-mapping source) inherits the same `F1`-checks-Monitor step ahead of or alongside its own OMTI-detect logic, then **pressing `F1` may enter the Monitor rather than skip to floppy** — plausible explanation for repeated difficulty getting a clean "skip HD" result via `F1` this session. **`F2` (the other bit in the same `AND 03h` check) has not been tried alone yet** and is now the better next candidate if the goal is specifically "skip HD boot" rather than "enter Monitor."

Separately, the exact `B2h` value tested at `0042h` (`CP B2h`) matches the base loader's own "foreign-standard-disk-format compatibility" signature (documented as being checked at `2FFFh` in the base loader, not `0xFFFF` as in the Sopp ROM's version) — see `genie3s_init_loader.md` for the full mechanism. Not fully reconciled: whether the Sopp ROM relocated this same check to `0xFFFF`, or is reusing the signature value `B2h` for a related-but-distinct purpose. Worth checking whether the Sopp ROM's disassembly touches `2FFFh` anywhere in the untraced portions.

## Not yet traced / open

- The relocated code bodies themselves (RAM `3800h` after each of the three separate copies into it, RAM `F700h` after the floppy-path relocation at `0057h`, RAM `4000h`-area clears at `00A4h`-`00B6h`) have only been reconstructed indirectly, from where they jump back into ROM — not independently disassembled at their RAM addresses. Doing that would need running the emulator interactively with breakpoints (`break`/`run` in `zbx`) rather than pure static disassembly, since their contents only exist in RAM after the relevant `LDIR`.
- The relocated code bodies themselves (RAM `3800h` after each of the three separate copies into it, RAM `F700h` after the floppy-path relocation at `0057h`, RAM `4000h`-area clears at `00A4h`-`00B6h`) have only been reconstructed indirectly, from where they jump back into ROM — not independently disassembled at their RAM addresses. Doing that would need running the emulator interactively with breakpoints (`break`/`run` in `zbx`) rather than pure static disassembly, since their contents only exist in RAM after the relevant `LDIR`.
- Helper subroutines `1175h`, `1185h`, `11DCh`, `1191h` (the low-level SASI CDB-clocking/phase routines) haven't been individually disassembled/named yet, only referenced by where they're called from.
- The exact SASI command byte(s) at the CDB template `11BCh` (what OMTI command is actually issued — almost certainly some form of REQUEST SENSE / TEST UNIT READY for the presence probe, then READ for the boot-sector load, per standard SASI convention, but not confirmed from the actual command bytes yet).
- No hard-disk `.hdv` image with a real boot sector has been built or tested against this yet — the `IX=4200h` hand-off is understood architecturally but has not been exercised end-to-end.
