#!/usr/bin/env python
import sys
import os
import subprocess
import serial.tools.list_ports
import glob
import platform


def list_usb_devices():
    """List all available USB serial ports with their details."""
    # Get all serial ports using pyserial
    ports = serial.tools.list_ports.comports()

    print("\n=== USB Serial Ports (via pyserial) ===")
    if not ports:
        print("No USB serial devices found via pyserial.")
    else:
        print(f"{'Device Path':<30} {'Description':<40} {'Hardware ID':<40}")
        print("-" * 110)

        for port in ports:
            print(f"{port.device:<30} {port.description:<40} {port.hwid:<40}")
            # Additional details if available
            if hasattr(port, "manufacturer") and port.manufacturer:
                print(f"  Manufacturer: {port.manufacturer}")
            if hasattr(port, "product") and port.product:
                print(f"  Product: {port.product}")
            if hasattr(port, "serial_number") and port.serial_number:
                print(f"  Serial Number: {port.serial_number}")
            print()

    # Get all devices in /dev that might be serial ports
    print("\n=== All potential USB devices in /dev ===")
    dev_paths = []
    patterns = [
        "/dev/tty*",
        "/dev/cu.*",
        "/dev/serial*",
        "/dev/usb*",
    ]

    for pattern in patterns:
        dev_paths.extend(glob.glob(pattern))

    if not dev_paths:
        print("No matching devices found in /dev.")
    else:
        dev_paths.sort()
        for path in dev_paths:
            dmx_indicator = " (Possible DMX controller)" if "usbserial" in path else ""
            print(f"{path}{dmx_indicator}")

    # Check for the specific DMX controller path from your code
    dmx_path = "/dev/cu.usbserial-EN419206"
    print(f"\n=== Checking for DMX controller at {dmx_path} ===")
    if os.path.exists(dmx_path):
        print(f"DMX controller found at {dmx_path}")
    else:
        print(f"DMX controller NOT found at {dmx_path}")

    # On macOS, use system_profiler for detailed USB information
    if platform.system() == "Darwin":
        print("\n=== Detailed USB Device Information (macOS) ===")
        try:
            result = subprocess.run(
                ["system_profiler", "SPUSBDataType"], capture_output=True, text=True
            )
            print(result.stdout)
        except Exception as e:
            print(f"Error running system_profiler: {e}")


if __name__ == "__main__":
    list_usb_devices()
