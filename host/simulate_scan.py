"""Pretend to be an attacker: knock on every decoy port."""
import socket
import time

from host.net_sentinel import DECOY_PORTS

for port in DECOY_PORTS:
    try:
        socket.create_connection(("127.0.0.1", port), timeout=1).close()
        print("knocked on", port)
    except OSError:
        print("port", port, "closed (is net_sentinel running?)")
    time.sleep(0.3)