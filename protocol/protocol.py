"""polly_packet binary frame protocol.

Frame: [0xAA][LEVEL][LEN][PAYLOAD x LEN][CRC8]
CRC-8 (poly 0x07, init 0x00) covers LEVEL, LEN and PAYLOAD.
"""
from dataclasses import dataclass

START_BYTE = 0xAA
LEVEL_INFO, LEVEL_WARN, LEVEL_CRIT = 0x01, 0x02, 0x03
MAX_PAYLOAD = 255

SHARED_KEY = b"pager"  # demo key

def crc8(data: bytes, poly: int = 0x07, init: int = 0x00) -> int:
    crc = init
    for b in data:
        crc ^= b
        for _ in range(8):
            if crc & 0x80:
                crc = ((crc << 1) ^ poly) & 0xFF
            else:
                crc = (crc << 1) & 0xFF
    return crc



def encode_frame(level: int, payload: bytes) -> bytes:
    if level not in (LEVEL_INFO, LEVEL_WARN, LEVEL_CRIT):
        raise ValueError("invalid alert level")
    if len(payload) > MAX_PAYLOAD:
        raise ValueError("payload too long")
    body = bytes([level, len(payload)]) + payload
    return bytes([START_BYTE]) + body + bytes([crc8(body)])



@dataclass
class Frame:
    level: int
    payload: bytes


class FrameParser:
    """Feed raw bytes as they arrive; get back complete, valid frames."""

    def __init__(self):
        self.buf = bytearray()

    def feed(self, data: bytes) -> list[Frame]:
        self.buf.extend(data)
        frames = []
        while True:
            i = self.buf.find(START_BYTE)
            if i == -1:
                self.buf.clear()
                break
            if i > 0:
                del self.buf[:i]
            if len(self.buf) < 3:
                break
            total = 4 + self.buf[2]
            if len(self.buf) < total:
                break
            body = bytes(self.buf[1:total - 1])
            level_ok = self.buf[1] in (LEVEL_INFO, LEVEL_WARN, LEVEL_CRIT)
            if level_ok and crc8(body) == self.buf[total - 1]:
                frames.append(Frame(self.buf[1], bytes(self.buf[3:total - 1])))
                del self.buf[:total]
            else:
                del self.buf[:1]  
        return frames

def xor_cipher(data: bytes, key: bytes) -> bytes:
    """Scramble or unscramble: the same call does both."""
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))