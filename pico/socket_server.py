# socket_server.py  – persistent control connection.
import socket, select, errno, time

# ping bookkeeping (used by main.py)
_last_ping_ms = 0
def update_ping_time():
    global _last_ping_ms
    _last_ping_ms = time.ticks_ms()

def get_last_ping_time():
    return _last_ping_ms

# Create the listening socket once from main.py.
def make_cmd_server(port: int = 1234):
    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", port))
    srv.listen(1)                  # single control connection is enough.
    srv.setblocking(False)
    print("CMD listening on", port)
    return srv

# internal state: one persistent control socket.
_sock = None

def poll_command(server_sock, pwm_led, ping_led):
    """
    Call this once per main loop.
    Accepts the first connection and keeps it open.
    Reads whatever lines arrive (PING / OFF) and acts on them.
    If the PC closes or an error occurs, resets and waits
    for the next accept.
    """
    global _sock

    # 1. Accept a connection if we don't have one yet.
    if _sock is None:
        readable, _, _ = select.select([server_sock], [], [], 0)
        if readable:
            _sock, _ = server_sock.accept()
            _sock.setblocking(False)
            # enable keep-alive on some ports/firmwares!?
            try:
                _sock.setsockopt(socket.SOL_SOCKET,
                                 getattr(socket, "SO_KEEPALIVE", 0), 1)
            except Exception:
                pass

    if _sock is None:
        return  # nothing to read this tick.

    # 2. Read any pending data (non-blocking).
    try:
        data = _sock.recv(64)
        if not data:
            # PC closed connection gracefully.
            _sock.close()
            _sock = None
            return

        for line in data.decode().splitlines():
            cmd = line.strip().upper()
            if cmd == "OFF":
                pwm_led.duty_u16(0)
                print("OFF")
            elif cmd == "PING":
                update_ping_time()
                ping_led.value(1)
                print("PING")

    except OSError as ex:
        if ex.errno != errno.EAGAIN:
            # real error => drop the socket and wait for a new accept.
            print("CTRL sock error:", ex)
            try:
                _sock.close()
            except Exception:
                pass
            _sock = None