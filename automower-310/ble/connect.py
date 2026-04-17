#!/usr/bin/env python3
"""
Connect to an Automower by BLE address and enumerate all GATT services,
characteristics, and descriptors. Reads any readable characteristics and
dumps their raw bytes.

Usage:
    python connect.py                     # auto-detect: scan, find, connect
    python connect.py --address AA:BB:CC:DD:EE:FF  # connect to known address
    python connect.py --raw               # also dump hex for every readable char

On macOS, addresses are UUIDs (e.g. 12345678-...), not MAC addresses.
Run scan.py first to discover the address for your platform, or omit
--address to auto-detect.
"""

import argparse
import asyncio
import sys
from datetime import datetime

from bleak import BleakClient, BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

from common import (
    WELL_KNOWN_CHARS,
    WELL_KNOWN_SERVICES,
    handle_ble_error,
    is_likely_automower,
    load_cached_device,
    save_device,
)


async def find_automower(timeout: float = 30.0) -> BLEDevice | None:
    cached = load_cached_device()
    if cached:
        print(f"  Cached device: {cached['name']} [{cached['address']}]")
        print("  Verifying it's still nearby...")
        device = await BleakScanner.find_device_by_address(cached["address"], timeout=10.0)
        if device:
            print(f"  Found cached device.")
            return device
        print("  Not found — falling back to full scan.")

    print(f"Scanning for Automower ({timeout}s)...")
    devices: dict[str, tuple[BLEDevice, AdvertisementData]] = {}

    def cb(device: BLEDevice, adv: AdvertisementData):
        if is_likely_automower(device, adv):
            devices[device.address] = (device, adv)
            print(f"  Found: {device.name or '(unknown)'} [{device.address}] RSSI={adv.rssi}")

    scanner = BleakScanner(detection_callback=cb)
    await scanner.start()
    await asyncio.sleep(timeout)
    await scanner.stop()

    if not devices:
        return None

    best_addr = max(devices, key=lambda a: devices[a][1].rssi)
    best_device = devices[best_addr][0]
    save_device(best_device)
    return best_device


def char_properties(char) -> str:
    props = []
    if "read" in char.properties:
        props.append("R")
    if "write" in char.properties:
        props.append("W")
    if "write-without-response" in char.properties:
        props.append("Wn")
    if "notify" in char.properties:
        props.append("N")
    if "indicate" in char.properties:
        props.append("I")
    return ",".join(props)


def try_decode(data: bytes) -> str:
    try:
        text = data.decode("utf-8")
        if text.isprintable():
            return repr(text)
    except (UnicodeDecodeError, ValueError):
        pass
    if len(data) == 1:
        return str(int.from_bytes(data, "little"))
    if len(data) == 2:
        return str(int.from_bytes(data, "little"))
    return data.hex(" ")


async def enumerate_services(address: str, dump_raw: bool):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"\n[{ts}] Connecting to {address}...")

    async with BleakClient(address, timeout=20.0) as client:
        print(f"Connected: {client.is_connected}")
        print(f"MTU: {client.mtu_size}\n")

        for service in client.services:
            svc_name = WELL_KNOWN_SERVICES.get(service.uuid, "")
            print(f"Service: {service.uuid}  {svc_name}")

            for char in service.characteristics:
                char_name = WELL_KNOWN_CHARS.get(char.uuid, "")
                props = char_properties(char)
                print(f"  Char: {char.uuid}  [{props}]  {char_name}")

                if "read" in char.properties:
                    try:
                        data = await client.read_gatt_char(char.uuid)
                        decoded = try_decode(data)
                        print(f"    Value: {decoded}")
                        if dump_raw and decoded != data.hex(" "):
                            print(f"    Raw:   {data.hex(' ')}")
                    except Exception as e:
                        print(f"    Read failed: {e}")

                for desc in char.descriptors:
                    print(f"    Descriptor: {desc.uuid}")
                    try:
                        data = await client.read_gatt_descriptor(desc.handle)
                        print(f"      Value: {try_decode(data)}")
                    except Exception as e:
                        print(f"      Read failed: {e}")

            print()


async def main(address: str | None, dump_raw: bool):
    if address is None:
        device = await find_automower()
        if device is None:
            print("No Automower found. Run scan.py --all to see all BLE devices nearby.")
            return
        address = device.address
        print(f"\nUsing {device.name or '(unknown)'} at {address}")

    await enumerate_services(address, dump_raw)

    pair_hint = {
        "win32": "Windows Bluetooth settings",
        "linux": "bluetoothctl (pair <addr>)",
        "darwin": "System Settings → Bluetooth",
    }.get(sys.platform, "your OS Bluetooth settings")
    print(f"Done. If pairing was required and failed, pair via {pair_hint} first.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Connect to Automower and enumerate GATT")
    parser.add_argument(
        "--address", type=str, default=None,
        help="BLE address (MAC on Windows/Linux, UUID on macOS). Omit to auto-detect.",
    )
    parser.add_argument("--raw", action="store_true", help="Also dump raw hex for every readable characteristic")
    args = parser.parse_args()
    try:
        asyncio.run(main(args.address, args.raw))
    except Exception as e:
        handle_ble_error(e)
