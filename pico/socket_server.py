# socket_server.py – persistent control connection.

import socket, select, errno, time
import utils
from utils import dbg


# Ping bookkeeping (main.py reads these helpers).
# ----------------------------------------------- #
_last_ping_ms = 0

def update_ping_time():
    global _last_ping_ms
    _last_ping_ms = time.ticks_ms()

def get_last_ping_time():
    return _last_ping_ms


# Server-socket creation (call once from main.py).
# ------------------------------------------------#
def make_cmd_server(port: int = 1234):
    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", port))
    srv.listen(1)          # One control connection is enough.
    srv.setblocking(False)
    dbg("CMD listening on", port)
    return srv

# One persistent client socket.
_sock = None

# Poll each main-loop tick.
# ------------------------ #
def poll_command(server_sock, ping_led):
    """
    Accept a connection if none is active, then read and act on
    any command lines. Drops the socket on error and waits for the
    next accept. Never blocks.
    """
    global _sock

    # 1. Accept phase.
    if _sock is None:
        r, _, _ = select.select([server_sock], [], [], 0)
        if r:
            _sock, _ = server_sock.accept()
            _sock.setblocking(False)
            # Best-effort keep-alive.
            opt = getattr(socket, "SO_KEEPALIVE", None)
            if opt is not None:
                try:
                    _sock.setsockopt(socket.SOL_SOCKET, opt, 1)
                except OSError:
                    pass

    if _sock is None:
        return                      # No client yet.

    # 2. Read phase (non-blocking).
    try:
        data = _sock.recv(64)
        if not data:                # Client closed.
            _sock.close()
            _sock = None
            return

        for raw in data.decode().splitlines():
            cmd = raw.strip().upper()

            if cmd == "START":
                utils.sys_on = True
                dbg("START => System up remotely")

            elif cmd == "STOP":
                utils.sys_on = False
                dbg("STOP => System down remotely")

            elif cmd == "PING":
                update_ping_time()
                ping_led.value(1)
                utils.last_blink_ms = time.ticks_ms()
                dbg("PING received")

            # --- future extensions.
            # elif cmd == "LOCK":
            #     ut.buttons_enabled = False
            #     dbg("LOCK => buttons disabled")
            # elif cmd == "UNLOCK":
            #     ut.buttons_enabled = True
            #     dbg("UNLOCK => buttons enabled")
            # elif cmd.startswith("SET MIN "):
            #     try:
            #         ut.min_dist = int(cmd.split()[2])
            #         dbg("SET MIN =>", main.min_dist, "mm")
            #     except (ValueError, IndexError):
            #         dbg("Bad SET MIN cmd:", cmd)
            # elif cmd.startswith("SET MAX "):
            #     try:
            #         ut.max_dist = int(cmd.split()[2])
            #         dbg("SET MAX =>", main.max_dist, "mm")
            #     except (ValueError, IndexError):
            #         dbg("Bad SET MAX cmd:", cmd)

    except OSError as ex:
        if ex.errno != errno.EAGAIN:    # Real error --> drop socket.
            dbg("CTRL socket error:", ex)
            try:
                _sock.close()
            except Exception:
                pass
            _sock = None
