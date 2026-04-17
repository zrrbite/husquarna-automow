# BLE tools — Automower 310

Python scripts (using [bleak](https://github.com/hbldh/bleak)) for sniffing and connecting to the Automower 310 over Bluetooth Low Energy.

## Requirements

```
pip install bleak
```

Needs a Bluetooth adapter. Most laptop adapters work; USB BT5.0 dongles also work.

## Scripts

### scan.py — find the mower

```bash
python scan.py              # scan 30s, show only Automower-like devices
python scan.py --duration 60  # scan longer
python scan.py --all        # show ALL BLE devices (useful if mower isn't detected by name)
```

### connect.py — enumerate GATT services

```bash
python connect.py                              # auto-detect and connect
python connect.py --address AA:BB:CC:DD:EE:FF  # connect to known address
python connect.py --address AA:BB:CC:DD:EE:FF --raw  # include raw hex dumps
```

May require pairing (PIN on mower display). If it fails, pair via Windows Bluetooth settings first, then retry.

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
