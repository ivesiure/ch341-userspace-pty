# Provenance and licence

## What was derived from where

The chip initialisation sequence in `ch341_pty.py` — the baud divisor arithmetic, registers
`0x9A` and `0xA1`, the `0x5F` version read and the prescaler bit handling — was **translated
from `drivers/usb/serial/ch341.c`** in the Linux kernel.

That file is **GPL-2.0-only**. Translating between languages does not create a new work: this
project is a derivative and inherits the same licence.

Authors credited in the header of the original `ch341.c` include, among others:
Frank A Kingswood, Werner Cornelius, Simon Lipp and Johan Hovold.

## What is deliberately absent, and why

🔴 The test tooling that accompanies this driver in the originating project implements the
**Klipper framing protocol**, derived from `klippy/msgproto.py`, which is **GPL-3.0**.

**GPL-2.0-only and GPL-3.0 cannot be combined.** That is why those tools are not in this
repository. This is not tidiness: it is the only way the package is distributable at all.

⚠️ If you add code here: anything derived from a GPL-3.0 project contaminates the whole and makes
it undistributable. Contributions must be original or GPL-2.0-compatible.

## Origin

Written to cut an Ender 3 V3 SE loose from the server it was tethered to, by running the Klipper
host on a rooted Android phone. The kernel there ships `usbserial`, `ftdi_sio`, `pl2303` and
`cdc_acm` — but no `ch341`, and recompiling the kernel was not on the table.
