import socket, gc, time


DATA_HOST = "192.168.10.220"
DATA_PORT = 4321
RETRY_MS  = 20_000           # 20-second back-off.

_last_try = 0                # global reconnect timer


# Enable TCP keep-alive (best-effort)
def enable_keepalive(sock):
    opt = getattr(socket, "SO_KEEPALIVE", None)
    if opt is not None:
        try:
            sock.setsockopt(socket.SOL_SOCKET, opt, 1)
        except OSError:
            pass

# Connection + back-off
def get_data_client():
    global _last_try
    now = time.ticks_ms()
    if time.ticks_diff(now, _last_try) < RETRY_MS:
        return None                           # still in cool-down
    _last_try = now

    try:
        s = socket.socket()
        s.settimeout(3)                       # 3-s dial timeout
        enable_keepalive(s)
        s.connect((DATA_HOST, DATA_PORT))     # blocking connect
        s.setblocking(False)                  # non-blocking afterwards
        s.settimeout(None)
        print("DATA socket connected to", DATA_HOST, ":", DATA_PORT)
        return s
    except OSError as ex:
        print("DATA connect failed:", ex)
        try:
            s.close()
        except Exception:
            pass
        gc.collect()
        return None

# Send pulse data
def send_distance(sock, dist_mm):
    try:
        sock.send("distance: %d\n" % dist_mm)
        return True
    except OSError as ex:
        print("DATA send error:", ex)
        try:
            sock.close()
        except Exception:
            pass
        gc.collect()
        return False
