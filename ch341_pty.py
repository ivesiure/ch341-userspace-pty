#!/usr/bin/env python3
"""Userspace CH341/CH340 USB-serial driver, exposed as a pty.

For machines whose kernel lacks the ch341 module: Android, containers,
locked-down NAS boxes, Steam Deck. Talks to the chip through plain ioctl
calls on /dev/bus/usb -- no kernel module, no libusb, no pyusb -- and
exposes the port as an ordinary pseudo-terminal that any program can open.

Pure Python, standard library only.

Environment:
    BAUD    line rate to program into the chip   (default 250000)
    LINK    stable symlink to create for the pty (default ~/printer)

Copyright (C) 2026 Ives Iure Magalhaes Ancelmo
SPDX-License-Identifier: GPL-2.0-only

The chip initialisation sequence (baud divisor, registers 0x9A and 0xA1,
the 0x5F version read) was TRANSLATED from drivers/usb/serial/ch341.c in
the Linux kernel, which is GPL-2.0-only. This file is therefore a
derivative work and inherits the same licence. See NOTICE.md.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY. See LICENSE for the full terms.
"""
import os, sys, fcntl, ctypes, struct, glob, select, threading, signal, time, termios, tty, traceback

BAUD     = int(os.environ.get("BAUD", "250000"))
VID, PID = "1a86", "7523"
LINK     = os.environ.get("LINK", os.path.expanduser("~/printer"))

def _ioc(d,t,nr,sz): return (d<<30)|(sz<<16)|(ord(t)<<8)|nr
CTRL,BULK,CLAIM = _ioc(3,'U',0,24), _ioc(3,'U',2,24), _ioc(2,'U',15,4)
CLK = 48000000
def _clk_div(ps,fact): return 1<<(12-3*ps-fact)
MIN_RATE = [CLK//(_clk_div(p,1)*512) for p in range(4)]

def baud_divisor(speed):
    """Translate a line rate into the CH341 prescaler/divisor register pair."""
    fact, ps = 1, 3
    while ps >= 0 and not speed > MIN_RATE[ps]: ps -= 1
    if ps < 0: raise SystemExit("baud rate out of range")
    div = _clk_div(ps,fact); d = CLK//(div*speed)
    if d < 9 or d > 255: d//=2; div*=2; fact=0
    if d < 2: raise SystemExit("invalid divisor")
    if 16*CLK//(div*d) - 16*speed >= 16*speed - 16*CLK//(div*(d+1)): d += 1
    if fact == 1 and d % 2 == 0: d//=2; fact=0
    return (0x100-d)<<8 | fact<<2 | ps

def find_device():
    """Locate the chip by VID:PID.

    The device number changes on every replug, so it cannot be hardcoded --
    walk sysfs and build the /dev/bus/usb path from busnum and devnum.
    """
    for path in sorted(glob.glob("/sys/bus/usb/devices/*/")):
        try:
            if open(path+"idVendor").read().strip() != VID: continue
            if open(path+"idProduct").read().strip() != PID: continue
            bus = int(open(path+"busnum").read()); dev = int(open(path+"devnum").read())
            return "/dev/bus/usb/%03d/%03d" % (bus,dev), path.rstrip("/")+":1.0"
        except (IOError, OSError, ValueError): continue
    raise SystemExit("CH341 %s:%s not found -- is the device plugged in?" % (VID,PID))

class Dev:
    """USBDEVFS ioctl wrapper. No libusb, no pyusb -- just fcntl.ioctl."""
    def __init__(self,path): self.fd = os.open(path, os.O_RDWR)
    def claim(self,iface): fcntl.ioctl(self.fd, CLAIM, struct.pack('I', iface))
    def ctrl(self,rtype,req,val,idx,length=0):
        buf = ctypes.create_string_buffer(max(length,1))
        fcntl.ioctl(self.fd, CTRL, struct.pack('=BBHHHI4xQ', rtype,req,val,idx,length,1000, ctypes.addressof(buf)))
        return buf.raw[:length]
    def bulk(self,ep,data=None,length=0,timeout=100):
        if data is not None: buf = ctypes.create_string_buffer(data,len(data)); length=len(data)
        else: buf = ctypes.create_string_buffer(max(length,1))
        pkt = bytearray(struct.pack('=III4xQ', ep, length, timeout, ctypes.addressof(buf)))
        n = fcntl.ioctl(self.fd, BULK, pkt, True)
        return buf.raw[:n]

dev_path, iface = find_device()
dev = Dev(dev_path); dev.claim(0)
version = dev.ctrl(0xC0, 0x5F, 0, 0, 2)[0]
dev.ctrl(0x40, 0xA1, 0, 0)
reg = baud_divisor(BAUD) | ((1<<7) if version > 0x27 else 0)
dev.ctrl(0x40, 0x9A, (0x13<<8)|0x12, reg)
if version >= 0x30: dev.ctrl(0x40, 0x9A, (0x25<<8)|0x18, 0xC3)
dev.ctrl(0x40, 0xA4, (~0x60)&0xffff, 0)

# Read the endpoint addresses from sysfs instead of assuming them.
endpoints = {}
for path in glob.glob(iface+"/ep_*"):
    addr = int(open(path+"/bEndpointAddress").read().strip(),16)
    endpoints.setdefault(open(path+"/type").read().strip(),[]).append(addr)
EP_OUT = [a for a in endpoints["Bulk"] if not a & 0x80][0]
EP_IN  = [a for a in endpoints["Bulk"] if a & 0x80][0]

master_fd, slave_fd = os.openpty()
# RAW on BOTH ends. Without it the line discipline eats protocol bytes:
# 0x11 and 0x13 are XON/XOFF, and some protocols use them as ordinary data.
for _fd in (master_fd, slave_fd):
    tty.setraw(_fd)
    attrs = termios.tcgetattr(_fd)
    attrs[0] &= ~(termios.IXON | termios.IXOFF | termios.IXANY | termios.ICRNL | termios.INLCR)
    attrs[1] &= ~termios.OPOST
    attrs[3] &= ~(termios.ECHO | termios.ICANON | termios.ISIG | termios.IEXTEN)
    attrs[6][termios.VMIN] = 1; attrs[6][termios.VTIME] = 0
    termios.tcsetattr(_fd, termios.TCSANOW, attrs)
pty_name = os.ttyname(slave_fd)
os.chmod(pty_name, 0o666)
# The pty number changes on every run, so publish a stable symlink.
try: os.remove(LINK)
except OSError: pass
os.symlink(pty_name, LINK)

PID_FILE = os.path.join(os.path.dirname(LINK), "ch341_pty.pid")
open(PID_FILE, "w").write(str(os.getpid()))
print("bridge up  (pid %d in %s)" % (os.getpid(), PID_FILE))
print("  usb        %s  (CH341 v0x%02x, %d baud)" % (dev_path, version, BAUD))
print("  endpoints  out=0x%02x in=0x%02x" % (EP_OUT, EP_IN))
print("  pty        %s" % pty_name)
print("  link       %s   <- point your program here" % LINK)
sys.stdout.flush()

stop = threading.Event()
stats = {"tx": 0, "rx": 0, "errors": 0}

def usb_to_pty():
    while not stop.is_set():
        try:
            chunk = dev.bulk(EP_IN, length=64, timeout=100)
            if chunk:
                os.write(master_fd, chunk); stats["rx"] += len(chunk)
        except OSError as e:
            if e.errno not in (110, 62):      # ETIMEDOUT / ETIME are normal
                stats["errors"] += 1; time.sleep(0.01)
                if e.errno in (19, 108):      # ENODEV / ESHUTDOWN
                    print("device went away:", e); stop.set()

def pty_to_usb():
    while not stop.is_set():
        try:
            ready, _, _ = select.select([master_fd], [], [], 0.2)
            if not ready: continue
            data = os.read(master_fd, 256)
            if data:
                dev.bulk(EP_OUT, data=data, timeout=500); stats["tx"] += len(data)
        except OSError as e:
            if e.errno == 5: time.sleep(0.05); continue   # EIO: nobody has the pty open
            stats["errors"] += 1; time.sleep(0.01)

def guard(fn, name):
    """A thread that dies silently looks exactly like a thread that is idle."""
    def wrapper():
        try:
            fn()
        except BaseException:
            print("!! thread %s DIED:" % name); traceback.print_exc(); sys.stdout.flush()
            stop.set()
    return wrapper

t1 = threading.Thread(target=guard(usb_to_pty, "usb->pty"), daemon=True); t1.start()
t2 = threading.Thread(target=guard(pty_to_usb, "pty->usb"), daemon=True); t2.start()

def cleanup(*_):
    stop.set()
    try: os.remove(LINK)
    except OSError: pass
    print("\nstopping  tx=%d rx=%d errors=%d" % (stats["tx"], stats["rx"], stats["errors"]))
    sys.exit(0)
signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)

while not stop.is_set():
    time.sleep(5)
    print("  tx=%d rx=%d errors=%d" % (stats["tx"], stats["rx"], stats["errors"])); sys.stdout.flush()
