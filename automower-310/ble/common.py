#!/usr/bin/env python3
"""Shared constants, detection logic, and platform helpers for BLE scripts."""

import json
import platform
import sys
from pathlib import Path

from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

HUSQVARNA_KEYWORDS = {"automower", "husqvarna", "gardena"}
HUSQVARNA_COMPANY_ID = 0x0426

WELL_KNOWN_SERVICES = {
    "00001800-0000-1000-8000-00805f9b34fb": "Generic Access",
    "00001801-0000-1000-8000-00805f9b34fb": "Generic Attribute",
    "0000180a-0000-1000-8000-00805f9b34fb": "Device Information",
    "0000180f-0000-1000-8000-00805f9b34fb": "Battery Service",
    "00001816-0000-1000-8000-00805f9b34fb": "Cycling Speed and Cadence",
}

WELL_KNOWN_CHARS = {
    "00002a00-0000-1000-8000-00805f9b34fb": "Device Name",
    "00002a01-0000-1000-8000-00805f9b34fb": "Appearance",
    "00002a04-0000-1000-8000-00805f9b34fb": "Peripheral Preferred Connection Parameters",
    "00002a19-0000-1000-8000-00805f9b34fb": "Battery Level",
    "00002a24-0000-1000-8000-00805f9b34fb": "Model Number String",
    "00002a25-0000-1000-8000-00805f9b34fb": "Serial Number String",
    "00002a26-0000-1000-8000-00805f9b34fb": "Firmware Revision String",
    "00002a27-0000-1000-8000-00805f9b34fb": "Hardware Revision String",
    "00002a28-0000-1000-8000-00805f9b34fb": "Software Revision String",
    "00002a29-0000-1000-8000-00805f9b34fb": "Manufacturer Name String",
}

DEVICE_CACHE = Path(__file__).parent / ".last_device.json"


def is_likely_automower(device: BLEDevice, adv: AdvertisementData) -> bool:
    name = (device.name or "").lower()
    if any(kw in name for kw in HUSQVARNA_KEYWORDS):
        return True
    if adv.manufacturer_data and HUSQVARNA_COMPANY_ID in adv.manufacturer_data:
        return True
    return False


def save_device(device: BLEDevice):
    """Cache the last-seen Automower address so connect.py can reuse it."""
    entry = {
        "address": device.address,
        "name": device.name,
        "platform": sys.platform,
    }
    DEVICE_CACHE.write_text(json.dumps(entry, indent=2), encoding="utf-8")


def load_cached_device() -> dict | None:
    if not DEVICE_CACHE.exists():
        return None
    try:
        entry = json.loads(DEVICE_CACHE.read_text(encoding="utf-8"))
        if entry.get("platform") != sys.platform:
            print(
                f"  Cached address was from {entry['platform']}, "
                f"but you're on {sys.platform} — rescanning."
            )
            return None
        return entry
    except (json.JSONDecodeError, KeyError):
        return None


def handle_ble_error(e: Exception):
    msg = str(e).lower()
    if "bluetooth" not in msg and "adapter" not in msg and "dbus" not in msg:
        raise e

    print(f"\nBluetooth error: {e}\n")
    os_name = platform.system()
    if os_name == "Windows":
        print("Check: Settings → Bluetooth & devices → toggle Bluetooth on.")
        print("If no adapter exists, a USB BT 5.0 dongle works (e.g. TP-Link UB500).")
    elif os_name == "Linux":
        print("Checklist:")
        print("  1. Is bluetoothd running?  systemctl status bluetooth")
        print("  2. Is your user in the bluetooth group?  groups $USER")
        print("     Fix: sudo usermod -aG bluetooth $USER  (then log out/in)")
        print("  3. Is the adapter powered on?  bluetoothctl power on")
        print("  4. D-Bus policy: /etc/dbus-1/system.d/bluetooth.conf must")
        print("     allow the bluetooth group to access org.bluez.")
    elif os_name == "Darwin":
        print("Check: System Settings → Bluetooth → toggle on.")
        print("If prompted, allow terminal access to Bluetooth in")
        print("System Settings → Privacy & Security → Bluetooth.")
    else:
        print(f"Unknown OS ({os_name}). Ensure Bluetooth is enabled and accessible.")
