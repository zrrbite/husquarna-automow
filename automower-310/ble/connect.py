"""
Connect to an Automower by BLE address and enumerate all GATT services,
characteristics, and descriptors. Reads any readable characteristics and
dumps their raw bytes.

Usage:
    python connect.py                     # auto-detect: scan, find, connect
    python connect.py --address AA:BB:CC:DD:EE:FF  # connect to known address
    python connect.py --address AA:BB:CC:DD:EE:FF --raw  # also dump hex for every readable char
"""

import argparse
import asyncio
from datetime import datetime

from bleak import BleakClient, BleakScanner
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


def is_likely_automower(device: BLEDevice, adv: AdvertisementData) -> bool:
    name = (device.name or "").lower()
    if any(kw in name for kw in HUSQVARNA_KEYWORDS):
        return True
    if adv.manufacturer_data and HUSQVARNA_COMPANY_ID in adv.manufacturer_data:
        return True
    return False


async def find_automower(timeout: float = 30.0) -> BLEDevice | None:
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
    return devices[best_addr][0]


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
    print("Done. If pairing was required and failed, pair via Windows Bluetooth settings first.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Connect to Automower and enumerate GATT")
    parser.add_argument("--address", type=str, default=None, help="BLE address (e.g. AA:BB:CC:DD:EE:FF)")
    parser.add_argument("--raw", action="store_true", help="Also dump raw hex for every readable characteristic")
    args = parser.parse_args()
    try:
        asyncio.run(main(args.address, args.raw))
    except Exception as e:
        if "bluetooth" in str(e).lower() or "adapter" in str(e).lower():
            print(f"\nBluetooth error: {e}")
            print("Check: is Bluetooth enabled in Windows Settings? Do you have a BT adapter?")
        else:
            raise
