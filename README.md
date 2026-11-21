# ── ୨ৎ ── ᴘᴏʟʟʏ ᴘᴀᴄᴋᴇᴛ ── ୨ৎ ──

Imagine a pocket-sized smart compact mirror, except it's secretly a covert cyber pager sitting on your desk.<br>Built with MicroPython firmware for a Raspberry Pi Pico, plus a Python virtual TCP simulator.

<!-- ![demo](docs/demo.gif) -->

## ✦ʚ♡ɞ✦ Architecture

```
polly_packet/
├── protocol/            
│   └── protocol.py      
├── host/                
│   ├── net_sentinel.py  
│   ├── send_alert.py    
│   ├── send_serial.py   
│   └── simulate_scan.py 
├── simulator/
│   └── virtual_pager.py 
├── firmware/            
│   ├── main.py         
│   └── pager_protocol.py  
├── tests_quick.py
└── tests_firmware_protocol.py
```

## ✦ʚ♡ɞ✦ Installation

* **Simulator (Windows):** Python `3.9+`

```
git clone https://github.com/sudochaithra/polly_packet.git
cd polly_packet
python -m simulator.virtual_pager     # terminal 1: the pager window
python -m host.net_sentinel           # terminal 2: the watcher
python -m host.simulate_scan          # terminal 3: pretend attacker
```

* **Hardware (Pico):** OLED (SDA `GP4`, SCL `GP5`) · NeoPixel (`GP16`) · Buzzer (`GP15`) · Button (`GP14`)

```
pip install pyserial mpremote
mpremote mip install ssd1306
mpremote cp firmware/pager_protocol.py :
mpremote cp firmware/main.py :
python -m host.send_serial COM5 crit "hello from the laptop" --wait
```

## ✦ʚ♡ɞ✦ Tests

```
python tests_quick.py                # 5 tests; CRC, round trip, byte-by-byte, corruption, scrambler
python tests_firmware_protocol.py    # parity-tested; firmware protocol matches the laptop's protocol
```

## ✦ʚ♡ɞ✦ Skills
![system design](https://img.shields.io/badge/System%20design-pager%20%26%20watcher-f472b6?style=flat-square)
![protocol design](https://img.shields.io/badge/Protocol%20design-framing%20%26%20resync-e879a8?style=flat-square)
![honeypots](https://img.shields.io/badge/Security-honeypot%20detection-c4106f?style=flat-square)
![threat modeling](https://img.shields.io/badge/Honest%20limits-documented-9d4edd?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.9+-ff69b4?style=flat-square&logo=python&logoColor=white)
![tkinter](https://img.shields.io/badge/tkinter-GUI%20%26%20canvas%20art-c084fc?style=flat-square)
![sockets](https://img.shields.io/badge/Sockets-TCP%20%2F%20UDP-a855f7?style=flat-square)
![threading](https://img.shields.io/badge/Threading-queues%20%26%20locks-7c3aed?style=flat-square)
![crc8](https://img.shields.io/badge/CRC--8-from%20scratch-ff2f9e?style=flat-square)
![xor](https://img.shields.io/badge/Crypto%20basics-XOR%20cipher-d946ef?style=flat-square) als
