"""MicroPython-safe copy of protocol/protocol.py (no dataclasses, no type hints)."""

START = b"\xaa"
LEVEL_INFO = 0x01
LEVEL_WARN = 0x02
LEVEL_CRIT = 0x03
LEVELS = (LEVEL_INFO, LEVEL_WARN, LEVEL_CRIT)
MAX_PAYLOAD = 255
SHARED_KEY = b"pager"


def crc8(data, poly=0x07, init=0x00):
    crc = init
    for b in data:
        crc ^= b
        for _ in range(8):
            if crc & 0x80:
                crc = ((crc << 1) ^ poly) & 0xFF
            else:
                crc = (crc << 1) & 0xFF
    return crc


def xor_cipher(data, key):
    return bytes([b ^ key[i % len(key)] for i, b in enumerate(data)])


def encode_frame(level, payload):
    body = bytes([level, len(payload)]) + payload
    return START + body + bytes([crc8(body)])


class FrameParser:
    """Feed bytes in, get a list of (level, payload) tuples out."""

    def __init__(self):
        self.buf = b""

    def feed(self, data):
        self.buf += data
        frames = []
        while True:
            i = self.buf.find(START)
            if i == -1:
                self.buf = b""
                break
            if i > 0:
                self.buf = self.buf[i:]
            if len(self.buf) < 3:
                break
            total = 4 + self.buf[2]
            if len(self.buf) < total:
                break
            body = self.buf[1:total - 1]
            if self.buf[1] in LEVELS and crc8(body) == self.buf[total - 1]:
                frames.append((self.buf[1], self.buf[3:total - 1]))
                self.buf = self.buf[total:]
            else:
                self.buf = self.buf[1:]  # false start, resync
        return frames