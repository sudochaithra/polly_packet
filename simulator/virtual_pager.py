"""Virtual pager: a spy-compact style tkinter window that acts like the real hardware."""
import math
import queue
import socket
import textwrap
import threading
import time
import tkinter as tk

from protocol.protocol import (FrameParser, xor_cipher, SHARED_KEY,
                               LEVEL_INFO, LEVEL_WARN, LEVEL_CRIT)

try:
    import winsound
except ImportError:
    winsound = None

HOST, PORT = "127.0.0.1", 9000
PATTERNS = {LEVEL_INFO: ".", LEVEL_WARN: "..", LEVEL_CRIT: "... --- ..."}

BG = "#2a1245"
BODY_TOP = (255, 150, 220)
BODY_BOT = (112, 44, 184)
BODY_EDGE = "#44157a"
SEAM = "#ffb8ec"
SHINE = "#fff0fb"
METAL = "#f6dcff"
METAL_EDGE = "#8a43c4"
WELL = "#5b1f93"
SCREEN_BG = "#160a2b"
SCREEN_EDGE = "#4a2a6e"
GREEN = "#6dff8f"
GREEN_DARK = "#0f3d22"
BLINK_ON = "#ffffff"
HEART_FACE = "#ff2e93"
HEART_PRESSED = "#c4106f"
HEART_SHINE = "#ff9be0"

HEART = ["00000000", "01100110", "11111111", "11111111",
         "11111111", "01111110", "00111100", "00011000"]
DIAMOND = ["00011000", "00111100", "01111110", "11111111",
           "11111111", "01111110", "00111100", "00011000"]
SKULL = ["00111100", "01111110", "11011011", "11011011",
         "01111110", "00111100", "00100100", "00000000"]
ICONS = {LEVEL_INFO: HEART, LEVEL_WARN: DIAMOND, LEVEL_CRIT: SKULL}
TITLES = {LEVEL_INFO: "NEW MESSAGE", LEVEL_WARN: "HEADS UP", LEVEL_CRIT: "INTRUDER"}
TINTS = {LEVEL_INFO: "#ff8ad8", LEVEL_WARN: "#ffe066", LEVEL_CRIT: "#ff4f8b"}


def blend(c1, c2, t):
    return "#%02x%02x%02x" % tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


def rounded(canvas, x1, y1, x2, y2, r, **kw):
    # tkinter has no rounded rectangle, so smooth a polygon instead
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
           x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return canvas.create_polygon(pts, smooth=True, **kw)


def heart_points(cx, cy, s):
    pts = []
    for i in range(72):
        t = i * math.pi * 2 / 72
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts += [cx + x * s, cy + (-y - 2.5) * s]
    return pts


def blink_timeline(pattern):
    """Turn a morse pattern into (light_on, seconds) steps, timed like the beeps."""
    steps = []
    for ch in pattern:
        if ch == " ":
            steps.append((False, 0.3))
            continue
        steps.append((True, 0.12 if ch == "." else 0.36))
        steps.append((False, 0.12))
    steps.append((False, 0.6))   # rest before the pattern repeats
    return steps


def play_pattern(pattern, stop):
    for ch in pattern:
        if stop.is_set():
            return
        if ch == " ":
            time.sleep(0.3)
            continue
        ms = 120 if ch == "." else 360
        try:
            if winsound:
                winsound.Beep(1000, ms)
            else:
                print("\a", end="", flush=True)
                time.sleep(ms / 1000)
        except RuntimeError:
            pass
        time.sleep(0.12)


def serve(server, frames):
    server.settimeout(1.0)
    while True:
        try:
            conn, _ = server.accept()
        except socket.timeout:
            continue
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
                    frames.put(frame)


class PagerApp:
    SX, SY, SW, SH = 56, 108, 288, 144   # oled area
    HX, HY = 200, 368                    # heart button centre

    def __init__(self, root, frames):
        self.root, self.frames = root, frames
        self.alerting = False
        self.alert_until = 0.0
        self.alert_start = 0.0
        self.blink_steps = []
        self.blink_cycle = 1.0
        self.stop_beep = threading.Event()

        root.title("polly_packet")
        root.configure(bg=BG)
        root.resizable(False, False)
        self.c = tk.Canvas(root, width=400, height=540, bg=BG, highlightthickness=0)
        self.c.pack()
        self.draw_body()
        self.draw_screen_frame()
        self.draw_blinker()
        self.draw_heart_button()
        self.draw_trim()
        self.show_idle()
        self.tick()

    def draw_body(self):
        c = self.c
        rounded(c, 18, 22, 382, 522, 132, fill=BODY_EDGE, outline="")
        steps = 44
        for i in range(steps):
            rounded(c, 20, 24 + i * 5, 380, 520, 130,
                    fill=blend(BODY_TOP, BODY_BOT, i / (steps - 1)), outline="")
        c.create_oval(66, 38, 250, 104, fill="white", stipple="gray12", outline="")
        rounded(c, 30, 34, 370, 510, 120, fill="", outline=SEAM, width=1)
        c.create_oval(170, 10, 230, 40, fill=METAL, outline=METAL_EDGE, width=2)
        c.create_line(184, 20, 216, 20, fill="white", width=2)

    def draw_screen_frame(self):
        c = self.c
        rounded(c, 44, 96, 356, 264, 30, fill=METAL, outline=METAL_EDGE, width=2)
        rounded(c, self.SX, self.SY, self.SX + self.SW, self.SY + self.SH, 16,
                fill=SCREEN_BG, outline=SCREEN_EDGE, width=2)
        c.create_polygon(self.SX + 6, self.SY + 6, self.SX + 150, self.SY + 6,
                         self.SX + 90, self.SY + self.SH - 6, self.SX + 6, self.SY + self.SH - 6,
                         fill="white", stipple="gray12", outline="", tags="gloss")

    def draw_blinker(self):
        c = self.c
        c.create_oval(266, 38, 318, 90, fill=METAL, outline=METAL_EDGE, width=2)
        c.create_oval(272, 44, 312, 84, fill=GREEN_DARK, outline="#2b7a45", width=2)
        self.gem = c.create_oval(277, 49, 307, 79, fill=GREEN, outline="")
        c.create_oval(281, 52, 291, 60, fill="white", outline="")
        c.create_oval(298, 68, 303, 73, fill="white", outline="")

    def draw_heart_button(self):
        c, hx, hy = self.c, self.HX, self.HY
        c.create_oval(hx - 94, hy - 94, hx + 94, hy + 94, fill=METAL, outline=METAL_EDGE, width=2)
        c.create_oval(hx - 85, hy - 85, hx + 85, hy + 85, fill=WELL, outline="#c58cf0", width=2)
        c.create_polygon(heart_points(hx, hy, 4.0), fill=METAL, outline=METAL_EDGE,
                         width=2, tags="ack")
        self.heart = c.create_polygon(heart_points(hx, hy, 3.5), fill=HEART_FACE,
                                      outline="white", width=2, tags="ack")
        c.create_oval(hx - 40, hy - 42, hx - 18, hy - 30, fill=HEART_SHINE, outline="", tags="ack")
        c.create_oval(hx - 36, hy - 39, hx - 26, hy - 34, fill="white", outline="", tags="ack")
        c.tag_bind("ack", "<ButtonPress-1>", lambda e: c.itemconfig(self.heart, fill=HEART_PRESSED))
        c.tag_bind("ack", "<ButtonRelease-1>", self.on_heart_release)
        c.tag_bind("ack", "<Enter>", lambda e: c.config(cursor="hand2"))
        c.tag_bind("ack", "<Leave>", lambda e: c.config(cursor=""))

    def draw_trim(self):
        c = self.c
        for i in range(6):
            x = 150 + i * 20
            c.create_oval(x - 4, 466, x + 4, 474, fill=BODY_EDGE, outline=SEAM)
        for x, y in [(70, 300), (330, 300), (62, 410), (338, 410), (96, 486), (304, 486)]:
            c.create_text(x, y, text="✦", fill=SHINE, font=("Segoe UI Symbol", 13))
        c.create_text(200, 494, text="p o l l y   p a c k e t", fill="#ffe0f6",
                      font=("Segoe UI", 9, "bold"))

    def on_heart_release(self, _event):
        self.c.itemconfig(self.heart, fill=HEART_FACE)
        self.acknowledge()

    def draw_bitmap(self, bitmap, x, y, px, color):
        for r, row in enumerate(bitmap):
            for col, bit in enumerate(row):
                if bit == "1":
                    self.c.create_rectangle(self.SX + x + col * px, self.SY + y + r * px,
                                            self.SX + x + (col + 1) * px,
                                            self.SY + y + (r + 1) * px,
                                            fill=color, outline="", tags="oled")

    def text(self, x, y, s, size=12, color=GREEN):
        self.c.create_text(self.SX + x, self.SY + y, text=s, anchor="nw", fill=color,
                           font=("Consolas", size, "bold"), tags="oled")

    def show_idle(self):
        self.c.delete("oled")
        self.draw_bitmap(HEART, 14, 12, 3, "#ff8ad8")
        self.text(48, 14, "STANDING BY", 16, "#ff8ad8")
        self.text(14, 60, "watching the net...")
        self.c.tag_raise("gloss")

    def show_alert(self, level, message):
        self.c.delete("oled")
        tint = TINTS[level]
        self.draw_bitmap(ICONS[level], 14, 12, 3, tint)
        self.text(48, 14, TITLES[level], 16, tint)
        for i, line in enumerate(textwrap.wrap(message, 26)[:4]):
            self.text(14, 48 + i * 20, line)
        self.c.tag_raise("gloss")

    def handle(self, frame):
        message = xor_cipher(frame.payload, SHARED_KEY).decode(errors="replace")
        self.stop_beep.set()                 # cut off the previous beeps
        self.stop_beep = threading.Event()
        self.show_alert(frame.level, message)
        self.alerting = True
        self.alert_start = time.time()
        self.blink_steps = blink_timeline(PATTERNS[frame.level])
        self.blink_cycle = sum(d for _, d in self.blink_steps)
        self.alert_until = float("inf") if frame.level == LEVEL_CRIT else time.time() + 8
        threading.Thread(target=play_pattern,
                         args=(PATTERNS[frame.level], self.stop_beep),
                         daemon=True).start()

    def acknowledge(self):
        self.stop_beep.set()
        self.alerting = False
        self.show_idle()

    def blinker_color(self, now):
        t = (now - self.alert_start) % self.blink_cycle
        for on, dur in self.blink_steps:
            if t < dur:
                return BLINK_ON if on else GREEN_DARK
            t -= dur
        return GREEN_DARK

    def tick(self):
        while True:
            try:
                self.handle(self.frames.get_nowait())
            except queue.Empty:
                break
        now = time.time()
        if self.alerting and now > self.alert_until:
            self.acknowledge()
        if self.alerting:
            color = self.blinker_color(now)
        else:
            color = blend((109, 255, 143), (40, 170, 90), (math.sin(now * 2) + 1) / 2)
        self.c.itemconfig(self.gem, fill=color)
        self.root.after(50, self.tick)


def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        server.bind((HOST, PORT))
    except OSError:
        print(f"Port {PORT} is busy. Close any other pager and retry.")
        return
    server.listen(1)
    frames = queue.Queue()
    threading.Thread(target=serve, args=(server, frames), daemon=True).start()
    root = tk.Tk()
    PagerApp(root, frames)
    root.mainloop()


if __name__ == "__main__":
    main()
