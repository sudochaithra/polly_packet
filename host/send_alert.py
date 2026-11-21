"""Send one alert frame to the pager.  Usage: python -m host.send_alert crit "message" """
import socket
import sys

from protocol.protocol import (encode_frame, xor_cipher, SHARED_KEY, MAX_PAYLOAD,
                               LEVEL_INFO, LEVEL_WARN, LEVEL_CRIT)

HOST, PORT = "127.0.0.1", 9000
LEVELS = {"info": LEVEL_INFO, "warn": LEVEL_WARN, "crit": LEVEL_CRIT}


def send_alert(level: int, text: str):
    scrambled = xor_cipher(text.encode()[:MAX_PAYLOAD], SHARED_KEY)
    frame = encode_frame(level, scrambled)
    with socket.create_connection((HOST, PORT), timeout=3) as s:
        s.sendall(frame)


if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[1] not in LEVELS:
        print('usage: python -m host.send_alert info|warn|crit "message"')
        sys.exit(1)
    try:
        send_alert(LEVELS[sys.argv[1]], " ".join(sys.argv[2:]))
        print("sent")
    except OSError:
        print("could not reach the pager. Is virtual_pager running?")