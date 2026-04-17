"""
Continuous BLE monitor — logs Automower advertisement data to a JSONL file
each time the mower comes within range.

Designed to run for hours; leave it open while the mower does its thing.
Each sighting is one JSON line with timestamp, RSSI, manufacturer data, etc.

Usage:
    python monitor.py                        # log to ble_log.jsonl
    python monitor.py --output my_log.jsonl  # custom output file
    python monitor.py --all                  # log ALL BLE devices (noisy)
"""

import argparse
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

from bleak import BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

HUSQVARNA_KEYWORDS = {"automower", "husqvarna", "gardena"}
HUSQVARNA_COMPANY_ID = 0x0426


def is_likely_automower(device: BLEDevice, adv: AdvertisementData) -> bool:
    name = (device.name or "").lower()
    if any(kw in name for kw in HUSQVARNA_KEYWORDS):
        return True
    if adv.manufacturer_data and HUSQVARNA_COMPANY_ID in adv.manufacturer_data:
        return True
    return False


class Monitor:
    def __init__(self, output_path: Path, show_all: bool):
        self.output_path = output_path
        self.show_all = show_all
        self.sighting_count = 0
        self.seen_addresses: set[str] = set()

    def on_detection(self, device: BLEDevice, adv: AdvertisementData):
        automower = is_likely_automower(device, adv)
        if not self.show_all and not automower:
            return

        now = datetime.now(timezone.utc)
        entry = {
            "timestamp": now.isoformat(),
            "address": device.address,
            "name": device.name,
            "rssi": adv.rssi,
            "tx_power": adv.tx_power,
            "is_automower": automower,
            "service_uuids": adv.service_uuids,
            "manufacturer_data": {
                f"0x{cid:04X}": data.hex()
                for cid, data in (adv.manufacturer_data or {}).items()
            },
            "service_data": {
                uuid: data.hex()
                for uuid, data in (adv.service_data or {}).items()
            },
        }

        with open(self.output_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

        self.sighting_count += 1
        is_new = device.address not in self.seen_addresses
        self.seen_addresses.add(device.address)

        ts = now.strftime("%H:%M:%S")
        tag = " ** AUTOMOWER **" if automower else ""
        new = " (new)" if is_new else ""
        print(
            f"[{ts}] {device.name or '?':20s} {device.address} "
            f"RSSI={adv.rssi:4d}{tag}{new}  "
            f"(total: {self.sighting_count} sightings, {len(self.seen_addresses)} devices)"
        )

    async def run(self):
        print(f"Monitoring BLE — logging to {self.output_path}")
        print("Press Ctrl+C to stop.\n")

        scanner = BleakScanner(detection_callback=self.on_detection)
        await scanner.start()
        try:
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass
        finally:
            await scanner.stop()
            print(f"\nStopped. {self.sighting_count} sightings logged to {self.output_path}")


async def main(output: str, show_all: bool):
    monitor = Monitor(Path(output), show_all)
    await monitor.run()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Continuously monitor Automower BLE")
    parser.add_argument("--output", type=str, default="ble_log.jsonl", help="Output JSONL file")
    parser.add_argument("--all", action="store_true", help="Log all BLE devices")
    args = parser.parse_args()
    try:
        asyncio.run(main(args.output, args.all))
    except KeyboardInterrupt:
        pass
