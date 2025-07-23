# socket_client.py – simple 200 ms blocking connect with watchdog retry
import socket, time, gc, errno
from utils import dbg

DATA_HOST  = "192.168.10.220"     # your PC’s IP
DATA_PORT  = 4321
_RETRY_SEC = 5                    # wait 5 s before another attempt

_last_try  = 0                    # ms timestamp
_stream    = None                 # active socket (or None)

# ---------------------------------------------------------------------
def _try_connect() -> bool:
    """Attempt a blocking connect with a 200 ms timeout."""
    global _stream, _last_try
    if _stream:                   # already up
        return True

    now = time.ticks_ms()
    if time.ticks_diff(now, _last_try) < _RETRY_SEC * 1000:
        return False              # still in back-off window
    _last_try = now

    try:
        s = socket.socket()
        s.settimeout(0.2)         # 200 ms max stall
        s.connect((DATA_HOST, DATA_PORT))
        s.settimeout(None)        # back to blocking
        s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        _stream = s
        dbg("DATA connected")
        return True
    except OSError as ex:
        dbg("DATA connect error:", ex)
        try:
            s.close()
        except Exception:
            pass
        _stream = None
        return False

# ---------------------------------------------------------------------
def _ensure_connection():
    """Call every loop; maintains the socket."""
    _try_connect()                # success / failure handled internally
    return _stream

# ---------------------------------------------------------------------
def write_line(msg: str):
    """Fire-and-forget send.  Drops payload if link is down."""
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
        gc.collect()
        _stream = None
        return False
