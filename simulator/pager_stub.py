"""Text-only stand-in for the pager. Listens on a TCP port and prints each frame."""
import socket
from protocol.protocol import FrameParser

HOST, PORT = "127.0.0.1", 9000
LEVEL_NAMES = {1: "INFO", 2: "WARN", 3: "CRIT"}


def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((HOST, PORT))
        server.listen(1)
        server.settimeout(1.0)
        print(f"pager listening on {HOST}:{PORT}  (Ctrl+C to quit)")
        try:
            while True:
                try:
                    conn, addr = server.accept()
                except socket.timeout:
                    continue
                print("laptop connected:", addr)
                conn.settimeout(1.0)
                parser = FrameParser()
                with conn:
                    while True:
                        try:
                            data = conn.recv(1024)
                        except socket.timeout:
                            continue
                        if not data:
                            break
                        for frame in parser.feed(data):
                            text = frame.payload.decode(errors="replace")
                            print(f"[{LEVEL_NAMES[frame.level]}] {text}")
                print("laptop disconnected")
        except KeyboardInterrupt:
            print("\npager off")


if __name__ == "__main__":
    main()