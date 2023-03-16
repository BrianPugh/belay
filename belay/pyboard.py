#!/usr/bin/env python3
#
# This file is part of the MicroPython project, http://micropython.org/
#
# The MIT License (MIT)
#
# Copyright (c) 2014-2021 Damien P. George
# Copyright (c) 2017 Paul Sokolovsky
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

"""
pyboard interface.

This module provides the Pyboard class, used to communicate with and
control a MicroPython device over a communication channel. Both real
boards and emulated devices (e.g. running in QEMU) are supported.
Various communication channels are supported, including a serial
connection, telnet-style network connection, external process
connection.

Example usage:

    import pyboard
    pyb = pyboard.Pyboard('/dev/ttyACM0')

Or:

    pyb = pyboard.Pyboard('192.168.1.1')

Then:

    pyb.enter_raw_repl()
    pyb.exec('import pyb')
    pyb.exec('pyb.LED(1).on()')
    pyb.exit_raw_repl()
"""

import ast
import atexit
import itertools
import os
import platform
import signal
import subprocess
import sys
import time
from pathlib import Path
from threading import Lock, Thread

from .webrepl import WebreplToSerial

try:
    stdout = sys.stdout.buffer
except AttributeError:
    # Python2 doesn't have buffer attr
    stdout = sys.stdout


def _kill_process(pid):
    try:
        if platform.system() == "Windows":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)])
        else:
            os.killpg(os.getpgid(pid), signal.SIGTERM)
    except ProcessLookupError:
        pass


def stdout_write_bytes(b):
    b = b.replace(b"\x04", b"")
    stdout.write(b)
    stdout.flush()


def _dummy_data_consumer(data):
    pass


class PyboardError(Exception):
    """An issue communicating with the board."""


class PyboardException(Exception):  # noqa: N818
    """Uncaught exception from the device."""

    def __str__(self):
        return "\n\n" + self.args[0]


class TelnetToSerial:
    def __init__(self, ip, user, password, read_timeout=None):
        self.tn = None
        import telnetlib

        self.tn = telnetlib.Telnet(ip, timeout=15)
        self.read_timeout = read_timeout
        if b"Login as:" in self.tn.read_until(b"Login as:", timeout=read_timeout):
            self.tn.write(bytes(user, "ascii") + b"\r\n")

            if b"Password:" in self.tn.read_until(b"Password:", timeout=read_timeout):
                # needed because of internal implementation details of the telnet server
                time.sleep(0.2)
                self.tn.write(bytes(password, "ascii") + b"\r\n")

                if b"for more information." in self.tn.read_until(
                    b'Type "help()" for more information.', timeout=read_timeout
                ):
                    # login successful
                    from collections import deque

                    self.fifo = deque()
                    return

        raise PyboardError("Failed to establish a telnet connection with the board.")

    def __del__(self):
        self.close()

    def close(self):
        if self.tn:
            self.tn.close()

    def read(self, size=1):
        while len(self.fifo) < size:
            timeout_count = 0
            data = self.tn.read_eager()
            if len(data):
                self.fifo.extend(data)
                timeout_count = 0
            else:
                time.sleep(0.25)
                if (
                    self.read_timeout is not None
                    and timeout_count > 4 * self.read_timeout
                ):
                    break
                timeout_count += 1

        data = b""
        while len(data) < size and len(self.fifo) > 0:
            data += bytes([self.fifo.popleft()])
        return data

    def write(self, data):
        self.tn.write(data)
        return len(data)

    @property
    def in_waiting(self):
        n_waiting = len(self.fifo)
        if not n_waiting:
            data = self.tn.read_eager()
            self.fifo.extend(data)
            return len(data)
        else:
            return n_waiting


class ProcessToSerial:
    """Execute a process and emulate serial connection using its stdin/stdout."""

    def __init__(self, cmd):
        import subprocess

        self.subp = subprocess.Popen(
            cmd,
            bufsize=0,
            shell=True,
            start_new_session=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
        )
        time.sleep(0.5)

        self.buf = bytearray()
        self.lock = Lock()

        def process_output():
            assert self.subp.stdout is not None  # noqa: S101
            while True:
                out = self.subp.stdout.read(1)
                if out == b"" and self.subp.poll() is not None:
                    break
                if out != b"":
                    with self.lock:
                        self.buf += out

        thread = Thread(target=process_output)
        thread.daemon = True
        thread.start()

        sleep_multiplier = float(os.environ.get("BELAY_SLEEP_MULTIPLIER", 1.0))
        time.sleep(5.0 * sleep_multiplier)  # Give process a chance to boot up.
        if platform.system() == "Windows":
            # Windows needs more time
            time.sleep(6.0 * sleep_multiplier)

        atexit.register(self.close)

    def close(self):
        _kill_process(self.subp.pid)
        atexit.unregister(self.close)

    def read(self, size=1):
        while len(self.buf) < size:
            # yield to the reading threads
            time.sleep(0.0001)

        with self.lock:
            data = self.buf[:size]
            self.buf = self.buf[size:]

        return data

    def write(self, data):
        self.subp.stdin.write(data)
        return len(data)

    @property
    def in_waiting(self):
        return len(self.buf)


class ProcessPtyToTerminal:
    """Creates a PTY process and prints slave PTY as first line of its output.

    Emulates serial connection using this PTY.
    """

    def __init__(self, cmd):
        import re
        import subprocess

        import serial

        self.subp = subprocess.Popen(
            cmd.split(),
            bufsize=0,
            shell=False,
            start_new_session=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        pty_line = self.subp.stderr.readline().decode("utf-8")
        m = re.search(r"/dev/pts/[0-9]+", pty_line)
        if not m:
            print("Error: unable to find PTY device in startup line:", pty_line)
            self.close()
            sys.exit(1)
        pty = m.group()
        # rtscts, dsrdtr params are to workaround pyserial bug:
        # http://stackoverflow.com/questions/34831131/pyserial-does-not-play-well-with-virtual-port
        self.ser = serial.Serial(pty, interCharTimeout=1, rtscts=True, dsrdtr=True)

    def close(self):
        import signal

        os.killpg(os.getpgid(self.subp.pid), signal.SIGTERM)

    def read(self, size=1):
        return self.ser.read(size)

    def write(self, data):
        return self.ser.write(data)

    @property
    def in_waiting(self):
        return self.ser.in_waiting


class Pyboard:
    def __init__(
        self,
        device: str,
        baudrate: int = 115200,
        user: str = "micro",
        password: str = "python",  # noqa: S107
        attempts: int = 1,
        exclusive: bool = True,
    ):
        """Micropython REPL compatibility class.

        Parameters
        ----------
        device: str
            Some device specificier like ``'/dev/ttyACM0'`` or ``'192.168.1.1'``.
        baudrate: int
            If a serial-like connection, this baudrate will be used.
        user: str
            If connection requires a username, this will be used.
        password: str
            If connection requires a password, this will be used.
        attempts: int
            Number of attempts to try and connect to board.
            If a ``<0`` value is provided, will infinitely try to connect.
        exclusive: bool
            If a serial-like connection, this configures the ``exclusive`` flag.
        """
        if attempts == 0:
            raise ValueError('"attempts" cannot be 0.')
        self.in_raw_repl = False
        self.use_raw_paste = True
        self._serial_buf = bytearray()
        if device.startswith("exec:"):
            self.serial = ProcessToSerial(device[len("exec:") :])
        elif device.startswith("execpty:"):
            self.serial = ProcessPtyToTerminal(device[len("qemupty:") :])
        elif (
            device
            and device[0].isdigit()
            and device[-1].isdigit()
            and device.count(".") == 3
        ):
            # device looks like an IP address
            self.serial = TelnetToSerial(device, user, password, read_timeout=10)
        elif device and device.startswith("ws://"):
            self.serial = WebreplToSerial(device, password, read_timeout=10)
        else:
            import serial

            # Set options, and exclusive if pyserial supports it
            serial_kwargs = {"baudrate": baudrate, "interCharTimeout": 1}
            if serial.__version__ >= "3.3":
                serial_kwargs["exclusive"] = exclusive

            for attempt_count in itertools.count(start=1):
                try:
                    self.serial = serial.Serial(device, **serial_kwargs)
                    break
                except OSError:
                    pass

                if attempt_count == attempts:
                    raise PyboardError("failed to access " + device)

                time.sleep(1.0)

        atexit.register(self.close)

    def close(self):
        if not self.serial:
            return
        self.exit_raw_repl()
        self.serial.close()
        self.serial = None
        atexit.unregister(self.close)

    def read_until(self, ending, timeout=10, data_consumer=None):
        """Read bytes until a specified ending pattern is reached.

        Parameters
        ----------
        data_consumer: Callable
            Function is called with data as soon as it becomes available.
            Does NOT wait for a newline.
        timeout: Union[None, float]
            Timeout in seconds.
            If None, no timeout.

        Returns
        -------
        data: bytes
            Data read up to, and including, ``ending``.
        """
        if data_consumer is None:
            data_consumer = _dummy_data_consumer

        i = self._serial_buf.find(ending)
        if i >= 0:
            out = self._serial_buf[: i + 1]
            self._serial_buf = self._serial_buf[i + 1 :]
            data_consumer(out)
        else:
            if timeout is None:
                timeout = float("inf")
            deadline = time.time() + timeout
            while True:
                i = max(1, min(2048, self.serial.in_waiting))
                data = self.serial.read(i)

                i = data.find(ending)
                if i >= 0:
                    data_consumer(data[: i + 1])

                    out = self._serial_buf + data[: i + 1]
                    self._serial_buf[:] = data[i + 1 :]

                    break
                else:
                    data_consumer(data)
                    self._serial_buf.extend(data)

                if time.time() > deadline:
                    raise PyboardError(
                        f"Timed out reading until {repr(ending)}\n    Received: {repr(self._serial_buf)}"
                    )

                time.sleep(0.01)

        return out

    def cancel_running_program(self):
        """Interrupts any running program."""
        self.serial.write(b"\r\x03\x03")  # ctrl-C twice: interrupt any running program

    def ctrl_d(self):
        # Note: When in raw repl mode, a soft-reset will NOT execute ``main.py``.
        self.serial.write(b"\x04")  # ctrl-D: soft reset

    def enter_raw_repl(self, soft_reset=True):
        # flush input (without relying on serial.flushInput())
        n = self.serial.in_waiting
        while n > 0:
            self.serial.read(n)
            n = self.serial.in_waiting
        self.cancel_running_program()
        self.exit_raw_repl()  # if device is already in raw_repl, b'>>>' won't be printed.
        self.read_until(b">>>")
        self.serial.write(b"\r\x01")  # ctrl-A: enter raw REPL
        if soft_reset:
            self.read_until(b"raw REPL; CTRL-B to exit\r\n>")
            self.ctrl_d()

        self.read_until(b"raw REPL; CTRL-B to exit\r\n")
        self.in_raw_repl = True

    def exit_raw_repl(self):
        self.serial.write(b"\r\x02")  # ctrl-B: enter friendly REPL
        self.in_raw_repl = False

    def follow(self, timeout, data_consumer=None):
        # wait for normal output (first EOF reception)
        data = self.read_until(b"\x04", timeout=timeout, data_consumer=data_consumer)
        data = data[:-1]

        # wait for error output
        data_err = self.read_until(b"\x04", timeout=timeout)
        data_err = data_err[:-1]

        # return normal and error output
        return data, data_err

    def raw_paste_write(self, command_bytes):
        # Read initial header, with window size.
        data = self.serial.read(2)
        window_size = data[0] | data[1] << 8
        window_remain = window_size

        # Write out the command_bytes data.
        i = 0
        while i < len(command_bytes):
            while window_remain == 0 or self.serial.in_waiting:
                data = self.serial.read(1)
                if data == b"\x01":
                    # Device indicated that a new window of data can be sent.
                    window_remain += window_size
                elif data == b"\x04":
                    # Device indicated abrupt end.  Acknowledge it and finish.
                    self.serial.write(b"\x04")
                    return
                else:
                    # Unexpected data from device.
                    raise PyboardError(f"unexpected read during raw paste: {data}")
            # Send out as much data as possible that fits within the allowed window.
            b = command_bytes[i : min(i + window_remain, len(command_bytes))]
            self.serial.write(b)
            window_remain -= len(b)
            i += len(b)

        # Indicate end of data.
        self.serial.write(b"\x04")

        # Wait for device to acknowledge end of data.
        self.read_until(b"\x04")

    def exec_raw_no_follow(self, command):
        if isinstance(command, bytes):
            command_bytes = command
        else:
            command_bytes = bytes(command, encoding="utf8")

        # check we have a prompt
        self.read_until(b">")

        if self.use_raw_paste:
            # Try to enter raw-paste mode.
            self.serial.write(b"\x05A\x01")
            data = self.serial.read(2)
            if data == b"R\x00":
                # Device understood raw-paste command but doesn't support it.
                pass
            elif data == b"R\x01":
                # Device supports raw-paste mode, write out the command using this mode.
                return self.raw_paste_write(command_bytes)
            else:
                # Device doesn't support raw-paste, fall back to normal raw REPL.
                self.read_until(b"w REPL; CTRL-B to exit\r\n>")
            # Don't try to use raw-paste mode again for this connection.
            self.use_raw_paste = False

        # Write command using standard raw REPL, 256 bytes every 10ms.
        for i in range(0, len(command_bytes), 256):
            self.serial.write(command_bytes[i : min(i + 256, len(command_bytes))])
            time.sleep(0.01)
        self.serial.write(b"\x04")

        # check if we could exec command
        data = self.serial.read(2)
        if data != b"OK":
            raise PyboardError("could not exec command (response: %r)" % data)

    def exec_raw(self, command, timeout=None, data_consumer=None):
        self.exec_raw_no_follow(command)
        return self.follow(timeout, data_consumer)

    def eval(self, expression):
        ret = self.exec(f"print({expression})")
        ret = ret.strip()
        return ret

    def exec(self, command, data_consumer=None):
        ret, ret_err = self.exec_raw(command, data_consumer=data_consumer)
        if ret_err:
            raise PyboardException(ret_err.decode())
        return ret

    def execfile(self, filename):
        pyfile = Path(filename).read_bytes()
        return self.exec(pyfile)

    def get_time(self):
        t = str(self.eval("pyb.RTC().datetime()"), encoding="utf8")[1:-1].split(", ")
        return int(t[4]) * 3600 + int(t[5]) * 60 + int(t[6])

    def fs_ls(self, src):
        cmd = (
            "import uos\nfor f in uos.ilistdir(%s):\n"
            " print('{:12} {}{}'.format(f[3]if len(f)>3 else 0,f[0],'/'if f[1]&0x4000 else ''))"
            % (("'%s'" % src) if src else "")
        )
        self.exec(cmd, data_consumer=stdout_write_bytes)

    def fs_cat(self, src, chunk_size=256):
        cmd = (
            "with open('%s') as f:\n while 1:\n"
            "  b=f.read(%u)\n  if not b:break\n  print(b,end='')" % (src, chunk_size)
        )
        self.exec(cmd, data_consumer=stdout_write_bytes)

    def fs_get(self, src, dest, chunk_size=256, progress_callback=None):
        dest = Path(dest)
        written = 0
        if progress_callback:
            src_size = int(self.exec("import os\nprint(os.stat('%s')[6])" % src))
        self.exec("f=open('%s','rb')\nr=f.read" % src)
        with dest.open("wb") as f:
            while True:
                data = bytearray()
                self.exec(
                    "print(r(%u))" % chunk_size,
                    data_consumer=lambda d: data.extend(d),  # noqa: B023
                )
                if not data.endswith(b"\r\n\x04"):
                    raise PyboardError

                try:
                    data = ast.literal_eval(str(data[:-3], "ascii"))
                except Exception as e:
                    raise PyboardError from e

                if not isinstance(data, bytes):
                    raise PyboardError

                if not data:
                    break
                f.write(data)
                written += len(data)
                if progress_callback:
                    progress_callback(written, src_size)
        self.exec("f.close()")

    def fs_put(self, src, dest, chunk_size=256, progress_callback=None):
        src = Path(src)
        written = 0
        src_size = src.stat().st_size
        self.exec("f=open('%s','wb')\nw=f.write" % dest)
        with src.open("rb") as f:
            while True:
                data = f.read(chunk_size)
                if not data:
                    break
                written += len(data)
                self.exec("w(" + repr(data) + ")")
                if progress_callback:
                    progress_callback(written, src_size)
        self.exec("f.close()")

    def fs_mkdir(self, dir):
        self.exec("import uos\nuos.mkdir('%s')" % dir)

    def fs_rmdir(self, dir):
        self.exec("import uos\nuos.rmdir('%s')" % dir)

    def fs_rm(self, src):
        self.exec("import uos\nuos.remove('%s')" % src)
