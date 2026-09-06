# Contributing

Bug reports, hardware reports and patches are all welcome. Open an issue or a pull request.

## Read this first: the licence constraint

This project is **GPL-2.0-only**, and not by preference. The chip initialisation is translated
from `drivers/usb/serial/ch341.c` in the Linux kernel, which is GPL-2.0 **without** the "or any
later version" clause. That makes this a derivative work with the same licence, permanently.

**The practical consequence for you:**

> Do not contribute code derived from a GPL-3.0 project.

Not because GPL-3.0 is worse, but because the two cannot be combined. GPL-2.0-only requires the
whole work to be distributed under GPL-2.0; GPL-3.0 requires the whole work to be distributed
under GPL-3.0. Both apply at once and neither can be satisfied — the result is a program that is
perfectly legal to write and to run, but that **nobody may lawfully distribute**, this project
included.

The most likely way to trip on this in practice: **Klipper is GPL-3.0.** Its `klippy/msgproto.py`
in particular is tempting to borrow from, because this driver is often used with Klipper. Don't.
The example in `examples/klipper.md` describes how to *use* the two together, which is fine;
copying Klipper code in here is not.

By opening a pull request you confirm that your contribution is your own work, or is compatible
with GPL-2.0-only.

## What is genuinely useful

In rough order of value:

1. **Reports from other chips.** This has been tested against exactly one: `1a86:7523`, CH340
   version `0x31`. The rest of the CH341 family shares the same init sequence in `ch341.c`, but
   nobody has run it here. If you try a CH341A, a CH9102 or anything else, say what happened —
   even "it did not work" is useful, with the output of the startup banner.
2. **Making `VID:PID` configurable.** Currently hardcoded.
3. **Reopening the device by itself when it re-enumerates.** Today the process exits and relies on
   a supervisor to bring it back.
4. **Passing through more serial semantics** — at minimum `TIOCMBIS`/`TIOCMBIC` for DTR/RTS, which
   is what stands between this and being usable with `avrdude`.

## Design constraints

Please keep these; they are the reason the project is useful where it is used.

- **Standard library only.** No `pyusb`, no `libusb`, no packaging. It has to run on a locked-down
  box where you cannot install anything, which is the entire point.
- **One file.** Someone should be able to copy `ch341_pty.py` onto a device over SSH and run it.
- **No kernel module, no root daemon beyond what `/dev/bus/usb` requires.**

## Practical notes

`main` is protected: pull requests need a review before merging, and force-pushes are blocked.
Fork the repository and open a PR against `main`.

Say what you tested on — chip, host, kernel, and whether the module was absent or just unused. A
patch that works on one setup and is untested elsewhere is still welcome; just label it as such,
because this project's whole value is knowing which claims were measured and which were assumed.
