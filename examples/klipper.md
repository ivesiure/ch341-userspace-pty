# Example: a Klipper host on a machine without `ch341`

The case this driver was written for. It applies to any host missing the module — the example
uses Android, but the shape is the same in a container or on a NAS.

## How it fits together

```
printer MCU → CH340 → USB → ch341_pty.py → pty → klippy
```

`klippy` opens the pty as if it were a serial port. It never knows that it isn't.

```ini
[mcu]
serial: /path/to/the/pty/symlink
baud: 115200
```

## 🔑 The two things that cost people time

**The `[mcu]` baud is fictional — and it must be 115200 even if the board runs at 250000.**

There is no UART on that side of the pseudo-terminal. The thing talking 250000 to the board is
this driver, at the chip. If you set `baud: 250000`, `pyserial` tries to configure a non-standard
rate on the pty and fails with:

```
NotImplementedError: non-standard baudrates are not supported on this platform
```

Do not fight `pyserial`. Set 115200 and move on — it does not change a single bit on the wire.

**Startup order matters: the bridge first, `klippy` second.**

The pty only exists while the driver is running. If `klippy` starts first it finds no such path;
and if the driver dies, `klippy` is left holding a dead file descriptor and **will not recover on
its own** — not even with `FIRMWARE_RESTART`, because that command travels over a link that no
longer exists. Only restarting the `klippy` process fixes it.

⚠️ Under a supervisor this is a trap of its own: `klippy` in that state **stays alive**, in
`shutdown`. As far as the supervisor is concerned everything is fine, so it restarts nothing. If
you want automatic recovery, you need something watching Klipper's *state*, not the existence of
the process.

## If the board gets stuck in `shutdown`

```
Can not update MCU config as it is shutdown
```

It recovers **in this order**, and you do not need to power-cycle the printer:

1. restart the `klippy` process (so it picks up the new pty)
2. `FIRMWARE_RESTART`

The other way round does not work.

## Verify by effect, not by absence of error

```bash
grep -c "Unhandled exception" klippy.log          # 0
grep -o "srtt=[0-9.]* rttvar=[0-9.]*" klippy.log | tail -3
grep -o "bytes_invalid=[0-9]*" klippy.log | tail -2
grep -c "Timer too close" klippy.log              # only shows up under load
```

💡 **The `klippy` log going quiet does not mean `klippy` died.** With the printer idle, no
subsystem declares itself active and Klipper writes nothing at all. Ask the API socket for the
state instead of reading the log.
