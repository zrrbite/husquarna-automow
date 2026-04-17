#!/usr/bin/env python3
"""
BLE advertisement scanner — finds Husqvarna Automower devices nearby.

Usage:
    python scan.py              # scan for 30 seconds
    python scan.py --duration 60  # scan for 60 seconds
    python scan.py --all        # show ALL BLE devices, not just likely Automowers
"""

import argparse
import asyncio
from datetime import datetime

from bleak import BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

from common import handle_ble_error, is_likely_automower, save_device


def format_manufacturer_data(mfr_data: dict[int, bytes]) -> str:
    if not mfr_data:
        return "(none)"
    parts = []
    for company_id, data in mfr_data.items():
        hex_data = data.hex(" ")
        parts.append(f"  company 0x{company_id:04X}: [{len(data)} bytes] {hex_data}")
    return "\n".join(parts)


def format_service_uuids(uuids: list[str]) -> str:
    if not uuids:
        return "(none)"
    return "\n".join(f"  {u}" for u in uuids)


def on_detection(device: BLEDevice, adv: AdvertisementData, *, show_all: bool):
    automower = is_likely_automower(device, adv)
    if not show_all and not automower:
        return

    if automower:
        save_device(device)

    ts = datetime.now().strftime("%H:%M:%S")
    tag = " ** AUTOMOWER **" if automower else ""
    print(f"\n{'='*60}")
    print(f"[{ts}] {device.name or '(unknown)'} — {device.address}{tag}")
    print(f"  RSSI: {adv.rssi} dBm")
    print(f"  Service UUIDs:\n{format_service_uuids(adv.service_uuids)}")
    print(f"  Manufacturer data:\n{format_manufacturer_data(adv.manufacturer_data)}")
    if adv.service_data:
        for uuid, data in adv.service_data.items():
            print(f"  Service data [{uuid}]: {data.hex(' ')}")
    print(f"  TX Power: {adv.tx_power}")


async def main(duration: int, show_all: bool):
    print(f"Scanning for BLE devices ({duration}s)...")
    print("Filtering for Husqvarna/Automower." if not show_all else "Showing ALL devices.")
    print("Leave this running while your mower passes by the window.\n")

    scanner = BleakScanner(
        detection_callback=lambda d, a: on_detection(d, a, show_all=show_all),
    )
    await scanner.start()
    await asyncio.sleep(duration)
    await scanner.stop()

    print(f"\nScan complete ({duration}s).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scan for Automower BLE advertisements")
    parser.add_argument("--duration", type=int, default=30, help="Scan duration in seconds")
    parser.add_argument("--all", action="store_true", help="Show all BLE devices")
    args = parser.parse_args()
    try:
        asyncio.run(main(args.duration, args.all))
    except Exception as e:
        handle_ble_error(e)
