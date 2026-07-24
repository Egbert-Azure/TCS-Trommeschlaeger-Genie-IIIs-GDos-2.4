#!/usr/bin/env python3
"""Build a blank (unformatted) OMTI .hdv hard-disk image for GDOS 2.4 testing.

Default geometry: 306 cylinders / 4 heads / 17 sectors/track / 512 bytes/sector
(~10.65MB, the classic "10MB" ST-506/MFM Winchester geometry shared by
Tandon TM602/TM603, Seagate ST-412, and most other drives of that class -
this is the documented capacity of the Genie IIIs' actual built-in hard
disk per the real GDOS 2.4 manual: "Eine im GENIE IIIs eingebaute 10 MByte
Harddisk wird von G-DOS 2.4 unterstuetzt", addressed as drive numbers 5
and 6). Use --cyls/--heads/--secs to build a different geometry (e.g. the
615/4/17 Seagate ST-225-class 21.4MB geometry used in earlier testing).

Header format: Matthew Reed's 256-byte .hdv header (see reed.h in
sdltrsOMTI, read there for reference only - this script does not depend
on or copy anything from that repo, it's a plain Python byte layout).
The data area is left zero-filled; GDOS's own HDFORMAT.CMD is expected to
lay down real structure on top interactively.
"""
import argparse

BYTES_PER_SECTOR = 512

def build_header(cyls: int, heads: int, secs_per_track: int, label: bytes) -> bytes:
    h = bytearray(256)
    h[0] = 0x56          # id1
    h[1] = 0xCB          # id2
    h[2] = 0x10          # ver 1.0
    h[3] = 0x00          # cksum (unused)
    h[4] = 1             # blks: header is 1 block of 256 bytes
    h[5] = 4             # mb4
    h[6] = 0              # media: 0 = hard disk
    h[7] = 0x00           # flag1: not write protected
    h[8] = 0x00           # flag2: bit0 = auto-boot -> off (booting via EPROM, not this flag)
    h[9] = 0x00           # flag3: reserved
    h[10] = 0x42          # crtr: 0x42 = "xtrs mkdisk"-style tool (closest fit)
    h[11] = 3             # dfmt: 3 = NEWDOS (closest available; inert since flag2 bit0 is off)
    # 12-25 reserved, stay 0
    h[26] = heads
    h[27] = (cyls >> 8) & 0xFF   # cylhi
    h[28] = cyls & 0xFF          # cyllo
    h[29] = heads * secs_per_track   # "sec" = sectors PER CYLINDER (all heads), not per track -
                                       # sdltrsOMTI's omti_open() does secs/heads to get sec/track,
                                       # and requires it to divide evenly
    h[30] = 0             # gran (deprecated)
    h[31] = 1             # dcyl (deprecated, "should be 1")
    lbl = label[:31]
    h[32:32 + len(lbl)] = lbl
    h[32 + len(lbl)] = 0
    return bytes(h)

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("out_path", nargs="?", default="HDV/g3s-gdos24-omti-10mb.hdv")
    p.add_argument("--cyls", type=int, default=306)
    p.add_argument("--heads", type=int, default=4)
    p.add_argument("--secs", type=int, default=17, help="sectors per track")
    p.add_argument("--label", default="GDOS24 OMTI 10MB")
    args = p.parse_args()

    header = build_header(args.cyls, args.heads, args.secs, args.label.encode("ascii"))
    data_size = args.cyls * args.heads * args.secs * BYTES_PER_SECTOR
    with open(args.out_path, "wb") as f:
        f.write(header)
        chunk = bytes(1024 * 1024)
        written = 0
        while written < data_size:
            n = min(len(chunk), data_size - written)
            f.write(chunk[:n])
            written += n
    total = 256 + data_size
    print(f"wrote {args.out_path}: {total} bytes "
          f"({args.cyls} cyl x {args.heads} heads x {args.secs} sec x {BYTES_PER_SECTOR} B "
          f"= {data_size} data bytes + 256-byte header, {data_size / 1e6:.2f} MB)")

if __name__ == "__main__":
    main()
