"""Send one alert to the pager over USB serial.
Usage: python -m host.send_serial COM5 crit "message" [--wait]
Needs: pip install pyserial
"""
import sys
import time

import serial  # pyserial

from protocol.protocol import (encode_frame, xor_cipher, SHARED_KEY, MAX_PAYLOAD,
                               FrameParser, LEVEL_INFO, LEVEL_WARN, LEVEL_CRIT)

LEVELS = {"info": LEVEL_INFO, "warn": LEVEL_WARN, "crit": LEVEL_CRIT}


def send_serial(port, level, text, wait=False):
    frame = encode_frame(level, xor_cipher(text.encode()[:MAX_PAYLOAD], SHARED_KEY))
    with serial.Serial(port, 115200, timeout=0.2) as s:
        s.write(frame)
        s.flush()
        if not wait:
            return True
        parser = FrameParser()
        deadline = time.time() + 60
        while time.time() < deadline:
            for f in parser.feed(s.read(64)):
                if f.payload == b"ACK":
                    return True
        return False


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--wait"]
    if len(args) < 3 or args[1] not in LEVELS:
        print('usage: python -m host.send_serial COM5 info|warn|crit "message" [--wait]')
        sys.exit(1)
    try:
        ok = send_serial(args[0], LEVELS[args[1]], " ".join(args[2:]), "--wait" in sys.argv)
        print("acknowledged on the pager" if "--wait" in sys.argv and ok
              else "no ACK within 60 s" if "--wait" in sys.argv else "sent")
    except serial.SerialException as e:
        print("could not open the port:", e)