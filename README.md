# ch341-userspace-pty

A **userspace CH341/CH340 USB-serial driver** in **pure Python** that exposes the port as an
ordinary **pty**.

For machines whose kernel **has no `ch341` module** and where recompiling is not an option:
Android, containers, locked-down NAS boxes, Steam Deck.

```bash
sudo python3 ch341_pty.py
# bridge up  (pid 12345 in /root/ch341_pty.pid)
#   usb        /dev/bus/usb/001/002  (CH341 v0x31, 250000 baud)
#   pty        /dev/pts/3
#   link       ~/printer   <- point your program here
```

Configure with two environment variables: `BAUD` (default `250000`) and `LINK`, the stable
symlink to create for the pty (default `~/printer`).

## How it works

It drives the chip through plain **`ioctl` calls on `/dev/bus/usb`** (USBDEVFS) — no kernel
module, no `libusb`, no `pyusb`, **standard library only**. It opens a pseudo-terminal and pumps
bytes between the two ends with two threads.

* Finds the chip by **VID:PID** through sysfs, because the device number changes on every replug.
* Reads the endpoint addresses from sysfs instead of assuming them.
* Publishes a stable symlink, because the pty number changes on every run.

## ⚠️ Read this before you use it

🔴 **A pty does not carry full serial semantics.** Parity, stop bits, modem control lines
(DTR/RTS) and hardware flow control **do not cross** the pseudo-terminal.

For what this was written for — Klipper, which runs 8N1 and does not touch DTR after init — that
does not matter. **If you need `avrdude`, or anything that toggles DTR to reset a board, you will
hit this wall.**

💡 The baud rate configured *on the pty* is **fictional**: there is no UART on that side of the
pseudo-terminal. The real rate is set by this driver, on the chip. If your program refuses a
non-standard rate (250000, say), **set it to 115200 and move on** — it changes nothing on the
wire.

## Requirements

* Python 3, standard library only
* Read/write access to `/dev/bus/usb` — usually root, or a udev rule

## Status

It works, and there is evidence. It carried the Klipper host of an Ender 3 V3 SE at 250000 baud
from an Android 10 phone: 44 minutes idle, a 4.7-minute pure-motion stress run, and a real
36.5-minute print, all with `Timer too close: 0` and an `srtt` of 6–8 ms.

⚠️ **Tested against a single chip** (`1a86:7523`, CH340 version `0x31`) on a single device. Other
members of the CH341 family share the same init sequence in `ch341.c`, but **were not exercised
here**.

## Not there yet

- [ ] Configurable `VID:PID` (currently hardcoded to `1a86:7523`)
- [ ] Reopen the device by itself when it re-enumerates — today the process dies and relies on a
      supervisor to bring it back
- [ ] Exercise other family members (CH341A, CH9102)
- [ ] Pass through what serial semantics can be passed: at least `TIOCMBIS`/`TIOCMBIC` for
      DTR/RTS

## Contributing

Reports from other chips are the single most useful thing you can send — this has been tested
against one. See `CONTRIBUTING.md`, which opens with the licence constraint you cannot guess:
**do not contribute code derived from a GPL-3.0 project**, Klipper included.

## Licence

**GPL-2.0-only**, because the chip initialisation is translated from
`drivers/usb/serial/ch341.c` in the Linux kernel. See `NOTICE.md` — including for why the test
tooling from the originating project is **not** here (it is GPL-3.0, which is incompatible).
