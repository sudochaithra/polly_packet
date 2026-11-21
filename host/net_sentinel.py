"""net_sentinel: sets out decoy ports and a UDP mailbox, then alerts the pager."""
import socket
import threading
import time
from collections import defaultdict

from protocol.protocol import LEVEL_INFO, LEVEL_WARN, LEVEL_CRIT
from host.send_alert import send_alert

BIND_IP = "127.0.0.1"          # demo mode: only this computer. Use "0.0.0.0" to watch your Wi-Fi.
DECOY_PORTS = [2222, 2323, 8888]   # pretend SSH, telnet and web server
UDP_PORT = 9100                # friends drop secret messages here
SCAN_WINDOW = 10               # seconds
SCAN_THRESHOLD = 3             # different decoy ports within the window = a scan

hits = defaultdict(dict)       # ip -> {port: time of last knock}
lock = threading.Lock()


def alert(level, text):
    print(f"[{time.strftime('%H:%M:%S')}] -> pager: {text}")
    try:
        send_alert(level, text)
    except OSError:
        print("   (pager is not running, alert not delivered)")


def record_hit(ip, port):
    now = time.time()
    with lock:
        seen = hits[ip]
        seen[port] = now
        for p in [p for p, t in seen.items() if now - t > SCAN_WINDOW]:
            del seen[p]                      # forget old knocks
        ports = sorted(seen)
        if len(ports) >= SCAN_THRESHOLD:
            seen.clear()
    if len(ports) >= SCAN_THRESHOLD:
        alert(LEVEL_CRIT, f"PORT SCAN from {ip} on ports {','.join(map(str, ports))}")
    else:
        alert(LEVEL_WARN, f"probe from {ip} on port {port}")


def decoy(port):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        server.bind((BIND_IP, port))
    except OSError:
        print(f"decoy port {port} is busy, skipping it")
        return
    server.listen(5)
    while True:
        conn, (ip, _) = server.accept()
        conn.close()
        record_hit(ip, port)


def udp_mailbox():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((BIND_IP, UDP_PORT))
    while True:
        data, (ip, _) = sock.recvfrom(1024)
        message = data.decode(errors="replace").strip()[:200]
        alert(LEVEL_INFO, f"msg from {ip}: {message}")


def main():
    for port in DECOY_PORTS:
        threading.Thread(target=decoy, args=(port,), daemon=True).start()
    threading.Thread(target=udp_mailbox, daemon=True).start()
    print(f"sentinel on guard. decoys: {DECOY_PORTS}, mailbox: udp {UDP_PORT}. Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nsentinel off")


if __name__ == "__main__":
    main()