# BLE tools — Automower 310

Python scripts (using [bleak](https://github.com/hbldh/bleak)) for sniffing and connecting to the Automower 310 over Bluetooth Low Energy. Cross-platform: Windows, Linux, macOS.

## Requirements

```bash
python3 -m venv .venv
source .venv/bin/activate   # macOS / Linux
# .venv\Scripts\activate    # Windows
pip install -r requirements.txt
```

This creates a virtual environment and installs `bleak`, which auto-pulls the right backend for your OS (WinRT on Windows, BlueZ/D-Bus on Linux, CoreBluetooth on macOS).

### Platform setup

**Windows**
- Settings → Bluetooth & devices → toggle on.
- Most laptop adapters work. For desktops without BT, a USB BT 5.0 dongle (e.g. TP-Link UB500) works.

**Linux (BlueZ)**
```bash
# 1. Ensure bluetoothd is running
sudo systemctl enable --now bluetooth

# 2. Add yourself to the bluetooth group
sudo usermod -aG bluetooth $USER
# Log out and back in for the group change to take effect.

# 3. Power on the adapter
bluetoothctl power on
```
If you get D-Bus permission errors after the above, check that `/etc/dbus-1/system.d/bluetooth.conf` grants access to the `bluetooth` group. Fallback: run as root.

**macOS**
- System Settings → Bluetooth → toggle on.
- When prompted, allow your terminal (Terminal.app, iTerm2, etc.) access in System Settings → Privacy & Security → Bluetooth.
- **Important:** macOS does not expose real MAC addresses. Device addresses are system-generated UUIDs (e.g. `12345678-1234-...`). These are local to your Mac and won't match the address shown on Windows/Linux for the same device. The scripts handle this — just use auto-detect or copy the address from `scan.py` output.

## Scripts

### scan.py — find the mower

```bash
python scan.py              # scan 30s, show only Automower-like devices
python scan.py --duration 60  # scan longer
python scan.py --all        # show ALL BLE devices (useful if mower isn't detected by name)
```

When an Automower is found, its address is cached in `.last_device.json` so `connect.py` can reuse it.

### connect.py — enumerate GATT services

```bash
python connect.py                              # auto-detect (uses cache, then scans)
python connect.py --address AA:BB:CC:DD:EE:FF  # connect to known address
python connect.py --raw                        # include raw hex dumps
```

May require pairing (PIN on mower display). If it fails:
- **Windows:** pair in Settings → Bluetooth.
- **Linux:** `bluetoothctl pair <address>`
- **macOS:** pair in System Settings → Bluetooth.

### monitor.py — long-running logger

```bash
python monitor.py                       # log Automower sightings to ble_log.jsonl
python monitor.py --output my_log.jsonl # custom file
python monitor.py --all                 # log everything (noisy)
```

Leave running while the mower roams. Each pass-by is logged as a JSON line with timestamp, RSSI, manufacturer data, service UUIDs, etc.

## Workflow

1. Run `scan.py --all` first to verify your Bluetooth adapter works and to spot the mower's name/address.
2. Note the address. Run `connect.py --address <addr> --raw` to dump all GATT data.
3. Leave `monitor.py` running to build a log over time. Bring the JSONL back here for analysis.

## Files (not committed)

- `.last_device.json` — cached address of last-seen Automower (platform-specific)
- `ble_log.jsonl` — monitor output log
