from protocol.protocol import *

assert crc8(b"123456789") == 0xF4
print("0 ok: crc8 matches the standard test value")

f = encode_frame(LEVEL_CRIT, b"10.0.0.42 SSH")
assert FrameParser().feed(f) == [Frame(LEVEL_CRIT, b"10.0.0.42 SSH")]
print("1 ok: round trip")

p, out = FrameParser(), []
for b in f:
    out += p.feed(bytes([b]))
assert len(out) == 1
print("2 ok: byte by byte")

bad = bytearray(f); bad[4] ^= 0xFF
good = encode_frame(LEVEL_INFO, b"hi")
assert FrameParser().feed(bytes(bad) + b"\x00\xAA" + good) == [Frame(LEVEL_INFO, b"hi")]
print("3 ok: survives corruption")

key = b"pager"
assert xor_cipher(xor_cipher(b"secret", key), key) == b"secret"
print("4 ok: xor cipher")