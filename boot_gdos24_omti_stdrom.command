#!/bin/bash
# Double-click this in Finder (or run from a terminal) to boot GDOS 2.4 under
# the STANDARD boot ROM (not the Sopp OMTI EPROM) with a hard disk attached
# anyway: DMK/G3S-GDOS24.DMK on disk0, ROM/g3s_8501004_bootrom_2732.bin as the
# boot ROM, HDV/g3s-gdos24-omti-10mb.hdv on omti0.
#
# WHY: the Sopp EPROM's own HD-boot-fail fallback path has a reproducible,
# 100%-repro bug in sdltrsOMTI (Z80 PC gets stuck at 002Bh, garbage screen -
# see README.md "Emulation" section). The standard ROM never probes OMTI at
# boot at all (it's 4KB with no OMTI code), so it boots exactly like the
# known-good floppy-only baseline while the hard disk stays attached for
# GDOS's own HDFORMAT.CMD/GENDIR.CMD to try talking to directly - this
# completely bypasses the Sopp ROM's broken boot-time fallback path. Use
# boot_gdos24_omti.command instead once that emulator bug is understood/fixed
# and you actually want to exercise the Sopp EPROM's own HD-boot logic.
#
# Every disk/hard/omti slot is passed explicitly (empty string to clear) so
# this never boots whatever was last left in ~/.sdltrs.t8c. Runs sdltrsOMTI's
# prebuilt binary in place - never writes into that repo.

set -e
cd "$(dirname "$0")"
REPO="$(pwd)"

SDLTRSOMTI_DIR="$HOME/Documents/GitHub/sdltrsOMTI"
ROM_PATH="$REPO/ROM/g3s_8501004_bootrom_2732.bin"
DISK0_PATH="$REPO/DMK/G3S-GDOS24.DMK"
OMTI_HDV="$REPO/HDV/g3s-gdos24-omti-10mb.hdv"
LOG_DIR="$REPO/logs"
LOG_FILE="$LOG_DIR/boot_gdos24_omti_stdrom_$(date +%Y%m%d_%H%M%S).log"

if [ ! -x "$SDLTRSOMTI_DIR/build/sdl2trs" ]; then
  echo "sdl2trs not found or not executable at: $SDLTRSOMTI_DIR/build/sdl2trs"
  echo "Build it first (in that repo): mkdir -p build && cd build && cmake .. && cmake --build ."
  read -n 1 -s -r -p "Press any key to close..."
  exit 1
fi

for f in "$ROM_PATH" "$DISK0_PATH" "$OMTI_HDV"; do
  if [ ! -f "$f" ]; then
    echo "Missing required file: $f"
    if [ "$f" = "$OMTI_HDV" ]; then
      echo "Build it with: python3 src/build_blank_omti_hdv.py"
    fi
    read -n 1 -s -r -p "Press any key to close..."
    exit 1
  fi
done

mkdir -p "$LOG_DIR"
echo "Logging to: $LOG_FILE"
echo "ROM (standard, not Sopp): $ROM_PATH"
echo "disk0: $DISK0_PATH"
echo "omti0: $OMTI_HDV"
echo

"$SDLTRSOMTI_DIR/build/sdl2trs" -model 1 \
  -rom "$ROM_PATH" \
  -disk0 "$DISK0_PATH" \
  -disk1 "" -disk2 "" -disk3 "" -disk4 "" -disk5 "" -disk6 "" -disk7 "" \
  -hard0 "" -hard1 "" -hard2 "" -hard3 "" \
  -omti0 "$OMTI_HDV" -omti1 "" \
  -diskdebug 0x3 -io 0xc \
  -nofullscreen 2>&1 | tee "$LOG_FILE"

echo
echo "sdl2trs exited. Log saved at: $LOG_FILE"
read -n 1 -s -r -p "Press any key to close..."
