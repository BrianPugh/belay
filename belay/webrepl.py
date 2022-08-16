"""
The MIT License (MIT).

Copyright (c) 2016 Damien P. George
Copyright (c) 2016 Paul Sokolovsky
Copyright (c) 2022 Jim Mussared

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""
import errno
import socket
import struct
import sys
from collections import deque
from pathlib import Path

from .exceptions import AuthenticationError

# Treat this remote directory as a root for file transfers
SANDBOX = ""
# SANDBOX = "/tmp/webrepl/"
DEBUG = 0

WEBREPL_REQ_S = "<2sBBQLH64s"
WEBREPL_PUT_FILE = 1
WEBREPL_GET_FILE = 2
WEBREPL_GET_VER = 3


def debugmsg(msg):
    if DEBUG:
        print(msg)


class WebreplError(Exception):
    pass


class Websocket:
    def __init__(self, s: socket.socket):
        self.s = s
        self.buf = b""

    def write(self, data):
        data_len = len(data)
        if data_len < 126:
            # TODO: hardcoded "binary" type
            hdr = struct.pack(">BB", 0x82, data_len)
        else:
            hdr = struct.pack(">BBH", 0x82, 126, data_len)
        self.s.send(hdr)
        self.s.send(data)

    def writetext(self, data: bytes):
        data_len = len(data)
        if data_len < 126:
            hdr = struct.pack(">BB", 0x81, data_len)
        else:
            hdr = struct.pack(">BBH", 0x81, 126, data_len)
        self.s.send(hdr)
        self.s.send(data)

    def recvexactly(self, sz):
        res = b""
        while sz:
            data = self.s.recv(sz)
            if not data:
                break
            res += data
            sz -= len(data)
        return res

    def read(self, size, text_ok=False, size_match=True):
        if not self.buf:
            while True:
                hdr = self.recvexactly(2)
                if len(hdr) != 2:
                    raise WebreplError
                fl, sz = struct.unpack(">BB", hdr)
                if sz == 126:
                    hdr = self.recvexactly(2)
                    if len(hdr) != 2:
                        raise WebreplError
                    (sz,) = struct.unpack(">H", hdr)
                if fl == 0x82:
                    break
                if text_ok and fl == 0x81:
                    break
                debugmsg("Got unexpected websocket record of type %x, skipping it" % fl)
                while sz:
                    skip = self.s.recv(sz)
                    debugmsg("Skip data: %s" % skip)
                    sz -= len(skip)
            data = self.recvexactly(sz)
            if len(data) != sz:
                raise WebreplError
            self.buf = data

        d = self.buf[:size]
        self.buf = self.buf[size:]
        if size_match and len(d) != size:
            raise WebreplError
        return d

    def ioctl(self, req, val):
        if req != 9 and val != 2:
            raise WebreplError


def login(ws, passwd):
    while True:
        c = ws.read(1, text_ok=True)
        if c == b":":
            if ws.read(1, text_ok=True) != b" ":
                raise WebreplError
            break
    ws.write(passwd.encode("utf-8") + b"\r")


def read_resp(ws):
    data = ws.read(4)
    sig, code = struct.unpack("<2sH", data)
    if sig != b"WB":
        raise WebreplError
    return code


def send_req(ws, op, sz=0, fname=b""):
    rec = struct.pack(WEBREPL_REQ_S, b"WA", op, 0, 0, sz, len(fname), fname)
    debugmsg("%r %d" % (rec, len(rec)))
    ws.write(rec)


def get_ver(ws):
    send_req(ws, WEBREPL_GET_VER)
    d = ws.read(3)
    d = struct.unpack("<BBB", d)
    return d


def put_file(ws, local_file, remote_file):
    local_file = Path(local_file)
    sz = local_file.stat().st_size
    dest_fname = (SANDBOX + remote_file).encode("utf-8")
    rec = struct.pack(
        WEBREPL_REQ_S, b"WA", WEBREPL_PUT_FILE, 0, 0, sz, len(dest_fname), dest_fname
    )
    debugmsg("%r %d" % (rec, len(rec)))
    ws.write(rec[:10])
    ws.write(rec[10:])
    if read_resp(ws) != 0:
        raise WebreplError
    cnt = 0
    with local_file.open("rb") as f:
        while True:
            sys.stdout.write("Sent %d of %d bytes\r" % (cnt, sz))
            sys.stdout.flush()
            buf = f.read(1024)
            if not buf:
                break
            ws.write(buf)
            cnt += len(buf)
    print()
    if read_resp(ws) != 0:
        raise WebreplError


def get_file(ws, local_file, remote_file):
    local_file = Path(local_file)
    src_fname = (SANDBOX + remote_file).encode("utf-8")
    rec = struct.pack(
        WEBREPL_REQ_S, b"WA", WEBREPL_GET_FILE, 0, 0, 0, len(src_fname), src_fname
    )
    debugmsg("%r %d" % (rec, len(rec)))
    ws.write(rec)
    if read_resp(ws) != 0:
        raise WebreplError
    with local_file.open("wb") as f:
        cnt = 0
        while True:
            ws.write(b"\0")
            (sz,) = struct.unpack("<H", ws.read(2))
            if sz == 0:
                break
            while sz:
                buf = ws.read(sz)
                if not buf:
                    raise OSError()
                cnt += len(buf)
                f.write(buf)
                sz -= len(buf)
                sys.stdout.write("Received %d bytes\r" % cnt)
                sys.stdout.flush()
    print()
    if read_resp(ws) != 0:
        raise WebreplError


def help(rc=0):
    exename = sys.argv[0].rsplit("/", 1)[-1]
    print(
        "%s - Perform remote file operations using MicroPython WebREPL protocol"
        % exename
    )
    print("Arguments:")
    print(
        "  [-p password] <host>:<remote_file> <local_file> - Copy remote file to local file"
    )
    print(
        "  [-p password] <local_file> <host>:<remote_file> - Copy local file to remote file"
    )
    print("Examples:")
    print("  %s script.py 192.168.4.1:/another_name.py" % exename)
    print("  %s script.py 192.168.4.1:/app/" % exename)
    print("  %s -p password 192.168.4.1:/app/script.py ." % exename)
    sys.exit(rc)


def error(msg):
    print(msg)
    sys.exit(1)


def parse_remote(remote):
    host, fname = remote.rsplit(":", 1)
    if fname == "":
        fname = "/"
    port = 8266
    if ":" in host:
        host, port = host.split(":")
        port = int(port)
    return (host, port, fname)


def client_handshake(sock):
    """Simplified client handshake.

    Works for MicroPython's websocket server implementation, but probably not
    for other servers.
    """
    cl = sock.makefile("rwb", 0)
    cl.write(
        b"""\
GET / HTTP/1.1\r
Host: echo.websocket.org\r
Connection: Upgrade\r
Upgrade: websocket\r
Sec-WebSocket-Key: foo\r
\r
"""
    )
    line = cl.readline()
    while 1:
        line = cl.readline()
        if line == b"\r\n":
            break


class WebsocketClosedError(Exception):
    """Attempted to use a closed websocket."""


class WebreplToSerial:
    def __init__(self, uri, password, read_timeout=None):
        self.fifo = deque()
        self.read_timeout = read_timeout

        if uri.startswith("ws://"):
            uri = uri[5:]
        host, *remain = uri.split(":", 1)
        port = int(remain[0]) if remain else 8266

        self.s = socket.socket()
        self.s.settimeout(read_timeout)
        self.s.connect((host, port))
        client_handshake(self.s)

        self.ws = Websocket(self.s)

        login(self.ws, password)
        response = self.read(1024)
        if response == b"\r\nAccess denied\r\n":
            raise AuthenticationError(f"Incorrect password: {repr(password)}")
        elif response != b"\r\nWebREPL connected\r\n>>> ":
            raise WebreplError(f"Unknown login response: {response}")

    def close(self):
        if self.s is not None:
            self.s.close()
        self.s = self.ws = None

    def write(self, data: bytes) -> int:
        if self.ws is None:
            raise WebsocketClosedError
        self.ws.writetext(data)
        return len(data)

    def read(self, size=1) -> bytes:
        if self.ws is None:
            raise WebsocketClosedError

        readin = self.ws.read(size, text_ok=True, size_match=False)
        self.fifo.extend(readin)

        data = b""
        while len(data) < size and len(self.fifo) > 0:
            data += bytes([self.fifo.popleft()])
        return data

    def inWaiting(self):
        if self.s is None or self.ws is None:
            raise WebsocketClosedError

        n_waiting = len(self.fifo) + len(self.ws.buf)
        if not n_waiting:
            self.s.setblocking(False)
            try:
                n_waiting = len(self.s.recv(1024, socket.MSG_PEEK))
            except BlockingIOError:
                pass
            except socket.error as e:
                if e == errno.EAGAIN or e == errno.EWOULDBLOCK:
                    pass
                else:
                    raise
            self.s.setblocking(True)
            return n_waiting
        else:
            return n_waiting
