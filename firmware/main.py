"""polly_packet firmware for Raspberry Pi Pico (MicroPython).

Wiring: OLED SDA=GP4 SCL=GP5 | NeoPixel DIN=GP16 | buzzer=GP15 | ACK button=GP14 to GND
Listens for polly_packet frames on USB serial, unscrambles them, then shows, flashes and beeps.
Hold the ACK button while plugging in to skip this program (service mode).
"""
import math
import select
import sys
import time

import micropython
import neopixel
import ssd1306
from machine import I2C, PWM, Pin

from pager_protocol import (FrameParser, encode_frame, xor_cipher, SHARED_KEY,
                            LEVEL_INFO, LEVEL_WARN, LEVEL_CRIT)

DEMO = False  # True = ignore USB and cycle sample alerts (for Wokwi, or testing without a laptop)

# ---- safety exit: hold the button at power-up to get your REPL back ----
button = Pin(14, Pin.IN, Pin.PULL_UP)
if button.value() == 0:
    raise SystemExit

# ---- hardware ----
i2c = I2C(0, sda=Pin(4), scl=Pin(5), freq=400000)
oled = ssd1306.SSD1306_I2C(128, 64, i2c)
pixel = neopixel.NeoPixel(Pin(16), 1)
buzzer = PWM(Pin(15))
buzzer.freq(1000)
buzzer.duty_u16(0)

# ---- look and feel ----
HEART = ["00000000", "01100110", "11111111", "11111111",
         "11111111", "01111110", "00111100", "00011000"]
DIAMOND = ["00011000", "00111100", "01111110", "11111111",
           "11111111", "01111110", "00111100", "00011000"]
SKULL = ["00111100", "01111110", "11011011", "11011011",
         "01111110", "00111100", "00100100", "00000000"]
ICONS = {LEVEL_INFO: HEART, LEVEL_WARN: DIAMOND, LEVEL_CRIT: SKULL}
TITLES = {LEVEL_INFO: "NEW MESSAGE", LEVEL_WARN: "HEADS UP", LEVEL_CRIT: "INTRUDER"}
PATTERNS = {LEVEL_INFO: ".", LEVEL_WARN: "..", LEVEL_CRIT: "... --- ..."}

# ---- state ----
alerting = False
alert_until = None   # None = stay until ACK
steps = []           # beep steps: (tone_on, milliseconds)
step_i = 0
step_end = 0
last_btn = 1


def to_text(data):
    """Printable ASCII only: the OLED font has nothing else."""
    return "".join([chr(b) if 32 <= b < 127 else "?" for b in data])


def draw_icon(bitmap, x, y, scale=2):
    for r, row in enumerate(bitmap):
        for c, bit in enumerate(row):
            if bit == "1":
                oled.fill_rect(x + c * scale, y + r * scale, scale, scale, 1)


def show_idle():
    oled.fill(0)
    draw_icon(HEART, 0, 0)
    oled.text("STANDING BY", 24, 4, 1)
    oled.text("watching the net", 0, 30, 1)
    oled.show()


def show_alert(level, message):
    oled.fill(0)
    draw_icon(ICONS[level], 0, 0)
    oled.text(TITLES[level], 24, 4, 1)
    lines = [message[i:i + 16] for i in range(0, len(message), 16)][:4]
    for n, line in enumerate(lines):
        oled.text(line, 0, 22 + n * 10, 1)
    oled.show()


# ---- Morse beeps as a state machine (never blocks) ----
def build_steps(pattern):
    out = []
    for ch in pattern:
        if ch == " ":
            out.append((False, 300))
        else:
            out.append((True, 120 if ch == "." else 360))
            out.append((False, 120))
    return out


def start_beeps(level):
    global steps, step_i, step_end
    steps = build_steps(PATTERNS[level])
    step_i = 0
    step_end = time.ticks_ms()


def stop_beeps():
    global steps, step_i
    steps = []
    step_i = 0
    buzzer.duty_u16(0)


def beep_update():
    global step_i, step_end
    now = time.ticks_ms()
    if time.ticks_diff(now, step_end) < 0:
        return
    if step_i >= len(steps):
        buzzer.duty_u16(0)
        return
    tone_on, ms = steps[step_i]
    buzzer.duty_u16(20000 if tone_on else 0)
    step_end = time.ticks_add(now, ms)
    step_i += 1


# ---- the jewel LED ----
def led_update():
    now = time.ticks_ms()
    if alerting:
        on = (now // 150) % 2 == 0
        pixel[0] = (90, 0, 60) if on else (0, 0, 0)
    else:
        t = (math.sin(now / 500) + 1) / 2   # 0..1, a slow breathing wave
        pixel[0] = (int(40 - 18 * t), int(10 + 2 * t), int(25 + 15 * t))
    pixel.write()


# ---- reacting to events ----
def handle(level, payload):
    global alerting, alert_until
    show_alert(level, to_text(xor_cipher(payload, SHARED_KEY)))
    alerting = True
    alert_until = None if level == LEVEL_CRIT else time.ticks_add(time.ticks_ms(), 8000)
    start_beeps(level)


def clear_alert(send_ack):
    global alerting, alert_until
    alerting = False
    alert_until = None
    stop_beeps()
    show_idle()
    if send_ack:
        try:
            sys.stdout.buffer.write(encode_frame(LEVEL_INFO, b"ACK"))
        except Exception:
            pass


def button_pressed():
    global last_btn
    v = button.value()
    pressed = v == 0 and last_btn == 1
    last_btn = v
    return pressed


# ---- demo alerts, so it runs without a laptop ----
SAMPLES = [(LEVEL_INFO, "hello bestie"),
           (LEVEL_WARN, "probe from 10.0.0.9 port 2222"),
           (LEVEL_CRIT, "PORT SCAN from 10.0.0.9")]


def main():
    micropython.kbd_intr(-1)  # let byte 0x03 (CRIT) through instead of "Ctrl+C"
    parser = FrameParser()
    poller = select.poll()
    poller.register(sys.stdin, select.POLLIN)
    demo_next = time.ticks_ms()
    demo_i = 0
    show_idle()

    while True:
        incoming = []
        if DEMO:
            if time.ticks_diff(time.ticks_ms(), demo_next) >= 0:
                level, text = SAMPLES[demo_i % len(SAMPLES)]
                demo_i += 1
                demo_next = time.ticks_add(time.ticks_ms(), 10000)
                incoming = parser.feed(encode_frame(level, xor_cipher(text.encode(), SHARED_KEY)))
        else:
            data = b""
            while len(data) < 64 and poller.poll(0):
                data += sys.stdin.buffer.read(1)
            if data:
                incoming = parser.feed(data)

        for level, payload in incoming:
            handle(level, payload)

        if alerting and alert_until is not None and time.ticks_diff(time.ticks_ms(), alert_until) >= 0:
            clear_alert(False)
        if button_pressed() and alerting:
            clear_alert(True)

        beep_update()
        led_update()
        time.sleep_ms(20)


main()