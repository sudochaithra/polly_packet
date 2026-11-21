"""Checks that the MicroPython protocol copy behaves exactly like the main one."""
import random
import sys

sys.path.insert(0, "firmware")
import pager_protocol as fw
from protocol import protocol as host

random.seed(1)

# 1. checksum, scrambler and frames
assert fw.crc8(b"123456789") == 0xF4
assert fw.xor_cipher(b"hello", b"pager") == host.xor_cipher(b"hello", b"pager")
for _ in range(200):
    level = random.choice([1, 2, 3])
    payload = bytes(random.randrange(256) for _ in range(random.randrange(0, 40)))
    assert fw.encode_frame(level, payload) == host.encode_frame(level, payload)

# 2. parsing of a messy stream: junk bytes, damaged frames, split delivery
stream = b""
for _ in range(50):
    level = random.choice([1, 2, 3])
    payload = bytes(random.randrange(256) for _ in range(random.randrange(0, 30)))
    frame = bytearray(host.encode_frame(level, payload))
    stream += bytes(random.randrange(256) for _ in range(random.randrange(0, 4)))
    if random.random() < 0.2:
        frame[random.randrange(len(frame))] ^= 0xFF
    stream += bytes(frame)

host_parser, fw_parser = host.FrameParser(), fw.FrameParser()
host_out, fw_out = [], []
i = 0
while i < len(stream):
    chunk = stream[i:i + random.randrange(1, 9)]
    host_out += [(f.level, f.payload) for f in host_parser.feed(chunk)]
    fw_out += fw_parser.feed(chunk)
    i += len(chunk)
assert host_out == fw_out
print("firmware protocol matches host protocol:", len(fw_out), "frames agree")