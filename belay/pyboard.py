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
pyboard interface

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

Note: if using Python2 then pyb.exec must be written as pyb.exec_.
To run a script from the local machine on the board and print out the results:

    import pyboard
    pyboard.execfile('test.py', device='/dev/ttyACM0')

This script can also be run directly.  To execute a local script, use:

    ./pyboard.py test.py

Or:

    python pyboard.py test.py

"""

import ast
import atexit
import itertools
import os
import sys
import time

from .webrepl import WebreplToSerial

try:
    stdout = sys.stdout.buffer
except AttributeError:
    # Python2 doesn't have buffer attr
    stdout = sys.stdout


def stdout_write_bytes(b):
    b = b.replace(b"\x04", b"")
    stdout.write(b)
    stdout.flush()


class PyboardError(Exception):
    """An issue communicating with the board."""


class PyboardException(Exception):
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

        raise PyboardError("Failed to establish a telnet connection with the board")

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

    def inWaiting(self):
        n_waiting = len(self.fifo)
        if not n_waiting:
            data = self.tn.read_eager()
            self.fifo.extend(data)
            return len(data)
        else:
            return n_waiting


class ProcessToSerial:
    "Execute a process and emulate serial connection using its stdin/stdout."

    def __init__(self, cmd):
        import subprocess

        self.subp = subp = subprocess.Popen(
            cmd,
            bufsize=0,
            shell=True,
            preexec_fn=os.setsid,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
        )

        # Initially was implemented with selectors, but that adds Python3
        # dependency. However, there can be race conditions communicating
        # with a particular child process (like QEMU), and selectors may
        # still work better in that case, so left inplace for now.
        #
        # import selectors
        # self.sel = selectors.DefaultSelector()
        # self.sel.register(self.subp.stdout, selectors.EVENT_READ)

        import select

        self.poll = select.poll()
        self.poll.register(self.subp.stdout.fileno())

        def cleanup():
            import signal

            try:
                os.killpg(os.getpgid(subp.pid), signal.SIGTERM)
            except ProcessLookupError:
                pass

        atexit.register(cleanup)

    def close(self):
        import signal

        os.killpg(os.getpgid(self.subp.pid), signal.SIGTERM)

    def read(self, size=1):
        data = b""
        while len(data) < size:
            data += self.subp.stdout.read(size - len(data))
        return data

    def write(self, data):
        self.subp.stdin.write(data)
        return len(data)

    def inWaiting(self):
        # res = self.sel.select(0)
        res = self.poll.poll(0)
        if res:
            return 1
        return 0


class ProcessPtyToTerminal:
    """Execute a process which creates a PTY and prints slave PTY as
    first line of its output, and emulate serial connection using
    this PTY."""

    def __init__(self, cmd):
        import re
        import subprocess

        import serial

        self.subp = subprocess.Popen(
            cmd.split(),
            bufsize=0,
            shell=False,
            preexec_fn=os.setsid,
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

    def inWaiting(self):
        return self.ser.inWaiting()


class Pyboard:
    def __init__(
        self,
        device: str,
        baudrate: int = 115200,
        user: str = "micro",
        password: str = "python",
        attempts: int = 1,
        exclusive: bool = True,
    ):
        """
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
                except (OSError, IOError):  # Py2 and Py3 have different errors
                    pass

                if attempt_count == attempts:
                    raise PyboardError("failed to access " + device)

                time.sleep(1.0)

    def close(self):
        self.serial.close()

    def read_until(self, min_num_bytes, ending, timeout=10, data_consumer=None):
        """
        Parameters
        ----------
        data_consumer: Callable
            Function is called with data as soon as it becomes available.
            Does NOT wait for a newline.
        timeout: Union[None, float]
            Timeout in seconds.
            If None, no timeout.
        """
        data = self.serial.read(min_num_bytes)
        if data_consumer:
            data_consumer(data)
        timeout_count = 0
        while True:
            if data.endswith(ending):
                break
            elif self.serial.inWaiting() > 0:
                new_data = self.serial.read(1)
                if data_consumer:
                    data_consumer(new_data)
                data = data + new_data
                timeout_count = 0
            else:
                timeout_count += 1
                if timeout is not None and timeout_count >= 100 * timeout:
                    raise PyboardError(
                        "Timed out reading until {repr(ending)}\n    Received: {repr(data)}"
                    )
                time.sleep(0.01)
        return data

    def enter_raw_repl(self, soft_reset=True):
        # flush input (without relying on serial.flushInput())
        n = self.serial.inWaiting()
        while n > 0:
            self.serial.read(n)
            n = self.serial.inWaiting()
        self.serial.write(b"\r\x03\x03")  # ctrl-C twice: interrupt any running program
        self.exit_raw_repl()  # if device is already in raw_repl, b'>>>' won't be printed.
        self.read_until(1, b">>>")
        self.serial.write(b"\r\x01")  # ctrl-A: enter raw REPL
        if soft_reset:
            self.read_until(1, b"raw REPL; CTRL-B to exit\r\n>")
            self.serial.write(b"\x04")  # ctrl-D: soft reset

            # Waiting for "soft reboot" independently to "raw REPL" (done below)
            # allows boot.py to print, which will show up after "soft reboot"
            # and before "raw REPL".
            self.read_until(1, b"soft reboot\r\n")
        self.read_until(1, b"raw REPL; CTRL-B to exit\r\n")
        self.in_raw_repl = True

    def exit_raw_repl(self):
        self.serial.write(b"\r\x02")  # ctrl-B: enter friendly REPL
        self.in_raw_repl = False

    def follow(self, timeout, data_consumer=None):
        # wait for normal output (first EOF reception)
        data = self.read_until(1, b"\x04", timeout=timeout, data_consumer=data_consumer)
        data = data[:-1]

        # wait for error output
        data_err = self.read_until(1, b"\x04", timeout=timeout)
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
            while window_remain == 0 or self.serial.inWaiting():
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
                    raise PyboardError(
                        "unexpected read during raw paste: {}".format(data)
                    )
            # Send out as much data as possible that fits within the allowed window.
            b = command_bytes[i : min(i + window_remain, len(command_bytes))]
            self.serial.write(b)
            window_remain -= len(b)
            i += len(b)

        # Indicate end of data.
        self.serial.write(b"\x04")

        # Wait for device to acknowledge end of data.
        self.read_until(1, b"\x04")

    def exec_raw_no_follow(self, command):
        if isinstance(command, bytes):
            command_bytes = command
        else:
            command_bytes = bytes(command, encoding="utf8")

        # check we have a prompt
        self.read_until(1, b">")

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
                self.read_until(1, b"w REPL; CTRL-B to exit\r\n>")
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
        ret = self.exec("print({})".format(expression))
        ret = ret.strip()
        return ret

    def exec(self, command, data_consumer=None):
        ret, ret_err = self.exec_raw(command, data_consumer=data_consumer)
        if ret_err:
            raise PyboardException(ret_err.decode())
        return ret

    def execfile(self, filename):
        with open(filename, "rb") as f:
            pyfile = f.read()
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
        if progress_callback:
            src_size = int(self.exec("import os\nprint(os.stat('%s')[6])" % src))
            written = 0
        self.exec("f=open('%s','rb')\nr=f.read" % src)
        with open(dest, "wb") as f:
            while True:
                data = bytearray()
                self.exec(
                    "print(r(%u))" % chunk_size, data_consumer=lambda d: data.extend(d)
                )
                assert data.endswith(b"\r\n\x04")
                try:
                    data = ast.literal_eval(str(data[:-3], "ascii"))
                    if not isinstance(data, bytes):
                        raise ValueError("Not bytes")
                except (UnicodeError, ValueError) as e:
                    raise PyboardError(
                        "fs_get: Could not interpret received data: %s" % str(e)
                    )
                if not data:
                    break
                f.write(data)
                if progress_callback:
                    written += len(data)
                    progress_callback(written, src_size)
        self.exec("f.close()")

    def fs_put(self, src, dest, chunk_size=256, progress_callback=None):
        if progress_callback:
            src_size = os.path.getsize(src)
            written = 0
        self.exec("f=open('%s','wb')\nw=f.write" % dest)
        with open(src, "rb") as f:
            while True:
                data = f.read(chunk_size)
                if not data:
                    break
                if sys.version_info < (3,):
                    self.exec("w(b" + repr(data) + ")")
                else:
                    self.exec("w(" + repr(data) + ")")
                if progress_callback:
                    written += len(data)
                    progress_callback(written, src_size)
        self.exec("f.close()")

    def fs_mkdir(self, dir):
        self.exec("import uos\nuos.mkdir('%s')" % dir)

    def fs_rmdir(self, dir):
        self.exec("import uos\nuos.rmdir('%s')" % dir)

    def fs_rm(self, src):
        self.exec("import uos\nuos.remove('%s')" % src)


def execfile(
    filename, device="/dev/ttyACM0", baudrate=115200, user="micro", password="python"
):
    pyb = Pyboard(device, baudrate, user, password)
    pyb.enter_raw_repl()
    output = pyb.execfile(filename)
    stdout_write_bytes(output)
    pyb.exit_raw_repl()
    pyb.close()


def filesystem_command(pyb, args, progress_callback=None, verbose=False):
    def fname_remote(src):
        if src.startswith(":"):
            src = src[1:]
        return src

    def fname_cp_dest(src, dest):
        src = src.rsplit("/", 1)[-1]
        if dest is None or dest == "":
            dest = src
        elif dest == ".":
            dest = "./" + src
        elif dest.endswith("/"):
            dest += src
        return dest

    cmd = args[0]
    args = args[1:]
    try:
        if cmd == "cp":
            srcs = args[:-1]
            dest = args[-1]
            if srcs[0].startswith("./") or dest.startswith(":"):
                op = pyb.fs_put
                fmt = "cp %s :%s"
                dest = fname_remote(dest)
            else:
                op = pyb.fs_get
                fmt = "cp :%s %s"
            for src in srcs:
                src = fname_remote(src)
                dest2 = fname_cp_dest(src, dest)
                if verbose:
                    print(fmt % (src, dest2))
                op(src, dest2, progress_callback=progress_callback)
        else:
            op = {
                "ls": pyb.fs_ls,
                "cat": pyb.fs_cat,
                "mkdir": pyb.fs_mkdir,
                "rmdir": pyb.fs_rmdir,
                "rm": pyb.fs_rm,
            }[cmd]
            if cmd == "ls" and not args:
                args = [""]
            for src in args:
                src = fname_remote(src)
                if verbose:
                    print("%s :%s" % (cmd, src))
                op(src)
    except PyboardError as er:
        print(str(er.args[2], "ascii"))
        pyb.exit_raw_repl()
        pyb.close()
        sys.exit(1)


_injected_import_hook_code = """\
import uos, uio
class _FS:
  class File(uio.IOBase):
    def __init__(self):
      self.off = 0
    def ioctl(self, request, arg):
      return 0
    def readinto(self, buf):
      buf[:] = memoryview(_injected_buf)[self.off:self.off + len(buf)]
      self.off += len(buf)
      return len(buf)
  mount = umount = chdir = lambda *args: None
  def stat(self, path):
    if path == '_injected.mpy':
      return tuple(0 for _ in range(10))
    else:
      raise OSError(-2) # ENOENT
  def open(self, path, mode):
    return self.File()
uos.mount(_FS(), '/_')
uos.chdir('/_')
from _injected import *
uos.umount('/_')
del _injected_buf, _FS
"""


def main():
    import argparse

    cmd_parser = argparse.ArgumentParser(description="Run scripts on the pyboard.")
    cmd_parser.add_argument(
        "-d",
        "--device",
        default=os.environ.get("PYBOARD_DEVICE", "/dev/ttyACM0"),
        help="the serial device or the IP address of the pyboard",
    )
    cmd_parser.add_argument(
        "-b",
        "--baudrate",
        default=os.environ.get("PYBOARD_BAUDRATE", "115200"),
        help="the baud rate of the serial device",
    )
    cmd_parser.add_argument(
        "-u", "--user", default="micro", help="the telnet login username"
    )
    cmd_parser.add_argument(
        "-p", "--password", default="python", help="the telnet login password"
    )
    cmd_parser.add_argument("-c", "--command", help="program passed in as string")
    cmd_parser.add_argument(
        "-w",
        "--wait",
        default=0,
        type=int,
        help="seconds to wait for USB connected board to become available",
    )
    group = cmd_parser.add_mutually_exclusive_group()
    group.add_argument(
        "--soft-reset",
        default=True,
        action="store_true",
        help="Whether to perform a soft reset when connecting to the board [default]",
    )
    group.add_argument(
        "--no-soft-reset",
        action="store_false",
        dest="soft_reset",
    )
    group = cmd_parser.add_mutually_exclusive_group()
    group.add_argument(
        "--follow",
        action="store_true",
        default=None,
        help="follow the output after running the scripts [default if no scripts given]",
    )
    group.add_argument(
        "--no-follow",
        action="store_false",
        dest="follow",
    )
    group = cmd_parser.add_mutually_exclusive_group()
    group.add_argument(
        "--exclusive",
        action="store_true",
        default=True,
        help="Open the serial device for exclusive access [default]",
    )
    group.add_argument(
        "--no-exclusive",
        action="store_false",
        dest="exclusive",
    )
    cmd_parser.add_argument(
        "-f",
        "--filesystem",
        action="store_true",
        help="perform a filesystem action: "
        "cp local :device | cp :device local | cat path | ls [path] | rm path | mkdir path | rmdir path",
    )
    cmd_parser.add_argument("files", nargs="*", help="input files")
    args = cmd_parser.parse_args()

    # open the connection to the pyboard
    try:
        pyb = Pyboard(
            args.device,
            args.baudrate,
            args.user,
            args.password,
            args.wait,
            args.exclusive,
        )
    except PyboardError as er:
        print(er)
        sys.exit(1)

    # run any command or file(s)
    if args.command is not None or args.filesystem or len(args.files):
        # we must enter raw-REPL mode to execute commands
        # this will do a soft-reset of the board
        try:
            pyb.enter_raw_repl(args.soft_reset)
        except PyboardError as er:
            print(er)
            pyb.close()
            sys.exit(1)

        def execbuffer(buf):
            try:
                if args.follow is None or args.follow:
                    ret, ret_err = pyb.exec_raw(
                        buf, timeout=None, data_consumer=stdout_write_bytes
                    )
                else:
                    pyb.exec_raw_no_follow(buf)
                    ret_err = None
            except PyboardError as er:
                print(er)
                pyb.close()
                sys.exit(1)
            except KeyboardInterrupt:
                sys.exit(1)
            if ret_err:
                pyb.exit_raw_repl()
                pyb.close()
                stdout_write_bytes(ret_err)
                sys.exit(1)

        # do filesystem commands, if given
        if args.filesystem:
            filesystem_command(pyb, args.files, verbose=True)
            del args.files[:]

        # run the command, if given
        if args.command is not None:
            execbuffer(args.command.encode("utf-8"))

        # run any files
        for filename in args.files:
            with open(filename, "rb") as f:
                pyfile = f.read()
                if filename.endswith(".mpy") and pyfile[0] == ord("M"):
                    pyb.exec("_injected_buf=" + repr(pyfile))
                    pyfile = _injected_import_hook_code
                execbuffer(pyfile)

        # exiting raw-REPL just drops to friendly-REPL mode
        pyb.exit_raw_repl()

    # if asked explicitly, or no files given, then follow the output
    if args.follow or (
        args.command is None and not args.filesystem and len(args.files) == 0
    ):
        try:
            ret, ret_err = pyb.follow(timeout=None, data_consumer=stdout_write_bytes)
        except PyboardError as er:
            print(er)
            sys.exit(1)
        except KeyboardInterrupt:
            sys.exit(1)
        if ret_err:
            pyb.close()
            stdout_write_bytes(ret_err)
            sys.exit(1)

    # close the connection to the pyboard
    pyb.close()


if __name__ == "__main__":
    main()
