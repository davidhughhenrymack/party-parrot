#!/usr/bin/env python
import os
import sys
import glob
import re
import subprocess
import platform
import serial.tools.list_ports


def scan_for_dmx_controllers():
    """
    Scan for potential DMX controllers connected to the system.
    Returns a list of potential DMX controller paths.
    """
    potential_dmx_paths = []

    # Method 1: Check using pyserial
    print("Scanning for DMX controllers using pyserial...")
    ports = serial.tools.list_ports.comports()

    for port in ports:
        # Look for FTDI or ENTTEC in the description or hardware ID
        desc = str(port.description).lower()
        hwid = str(port.hwid).lower()

        if any(
            keyword in desc or keyword in hwid
            for keyword in ["ftdi", "enttec", "dmx", "usb-serial"]
        ):
            print(f"Potential DMX controller found: {port.device}")
            print(f"  Description: {port.description}")
            print(f"  Hardware ID: {port.hwid}")
            if hasattr(port, "manufacturer") and port.manufacturer:
                print(f"  Manufacturer: {port.manufacturer}")
            if hasattr(port, "product") and port.product:
                print(f"  Product: {port.product}")
            if hasattr(port, "serial_number") and port.serial_number:
                print(f"  Serial Number: {port.serial_number}")
            potential_dmx_paths.append(port.device)

    # Method 2: Check /dev for usbserial devices (macOS/Linux)
    if platform.system() in ["Darwin", "Linux"]:
        print("\nScanning /dev for potential USB serial devices...")
        patterns = ["/dev/tty.usbserial*", "/dev/cu.usbserial*", "/dev/ttyUSB*"]

        for pattern in patterns:
            for path in glob.glob(pattern):
                if path not in potential_dmx_paths:
                    print(f"Potential DMX controller found: {path}")
                    potential_dmx_paths.append(path)

    # Method 3: On macOS, use system_profiler for more detailed info
    if platform.system() == "Darwin":
        print("\nScanning using system_profiler...")
        try:
            result = subprocess.run(
                ["system_profiler", "SPUSBDataType"], capture_output=True, text=True
            )

            # Look for FTDI or ENTTEC in the output
            output = result.stdout.lower()
            if "ftdi" in output or "enttec" in output:
                print("Found references to FTDI or ENTTEC in system_profiler output.")
                print("Check the full system_profiler output for more details.")
        except Exception as e:
            print(f"Error running system_profiler: {e}")

    return potential_dmx_paths


def update_dmx_path(new_path):
    """
    Update the DMX controller path in the codebase.
    """
    dmx_utils_path = "parrot/utils/dmx_utils.py"

    if not os.path.exists(dmx_utils_path):
        print(f"Error: Could not find {dmx_utils_path}")
        return False

    with open(dmx_utils_path, "r") as f:
        content = f.read()

    # Find the line with usb_path
    pattern = r'usb_path\s*=\s*"([^"]*)"'
    match = re.search(pattern, content)

    if not match:
        print(f"Error: Could not find usb_path in {dmx_utils_path}")
        return False

    old_path = match.group(1)

    # Replace the path
    new_content = re.sub(pattern, f'usb_path = "{new_path}"', content)

    with open(dmx_utils_path, "w") as f:
        f.write(new_content)

    print(
        f"Updated DMX controller path from '{old_path}' to '{new_path}' in {dmx_utils_path}"
    )
    return True


def main():
    print("DMX Controller Scanner")
    print("======================")

    # Current DMX path in the code
    dmx_utils_path = "parrot/utils/dmx_utils.py"
    current_path = None

    if os.path.exists(dmx_utils_path):
        with open(dmx_utils_path, "r") as f:
            content = f.read()

        pattern = r'usb_path\s*=\s*"([^"]*)"'
        match = re.search(pattern, content)

        if match:
            current_path = match.group(1)
            print(f"Current DMX controller path in code: {current_path}")
            print(f"Path exists: {os.path.exists(current_path)}")

    # Scan for potential DMX controllers
    print("\nScanning for potential DMX controllers...")
    potential_paths = scan_for_dmx_controllers()

    if not potential_paths:
        print("\nNo potential DMX controllers found.")
        return

    print("\nPotential DMX controller paths:")
    for i, path in enumerate(potential_paths, 1):
        print(f"{i}. {path}")

    # Ask if user wants to update the path
    print("\nDo you want to update the DMX controller path in the code?")
    print("Enter the number of the path to use, or 'n' to skip: ", end="")
    choice = input().strip()

    if choice.lower() == "n":
        print("Skipping path update.")
        return

    try:
        index = int(choice) - 1
        if 0 <= index < len(potential_paths):
            new_path = potential_paths[index]
            update_dmx_path(new_path)
        else:
            print("Invalid selection.")
    except ValueError:
        print("Invalid input.")


if __name__ == "__main__":
    main()
