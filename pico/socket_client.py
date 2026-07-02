# socket_client.py - simple 200 ms blocking connect with watchdog retry
import gc
import socket
import time

from boot import PC_IP
from utils import dbg


DATA_HOST = PC_IP
DATA_PORT = 4321
_RETRY_SEC = 5  # Wait before another connection attempt.

_last_try = 0
_stream = None


def _try_connect() -> bool:
    """Attempt a blocking connection with a 200 ms timeout."""
    global _stream, _last_try

    if _stream is not None:
        return True

    now = time.ticks_ms()

    if time.ticks_diff(now, _last_try) < _RETRY_SEC * 1000:
        return False

    s = None

    try:
        s = socket.socket()
        s.settimeout(0.2)
        s.connect((DATA_HOST, DATA_PORT))
        s.settimeout(None)
        s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

        _stream = s
        _last_try = now

        dbg("DATA connected")
        return True

    except OSError as ex:
        dbg("DATA connect error:", ex)

        if s is not None:
            try:
                s.close()
            except Exception:
                pass

        _stream = None
        _last_try = now
        return False


def _ensure_connection():
    """Maintain the data connection and return the active socket."""
    _try_connect()
    return _stream


def write_line(msg: str) -> bool:
    """Send one newline-terminated message, or drop it if disconnected."""
    global _stream

    if _stream is None:
        return False

    try:
        _stream.write((msg + "\n").encode())
        return True

    except OSError as ex:
        dbg("DATA send error:", ex)

        try:
            _stream.close()
        except Exception:
            pass

        _stream = None
        gc.collect()
        return False