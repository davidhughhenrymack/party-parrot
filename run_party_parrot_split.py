#!/usr/bin/env python3
"""
Party Parrot Split System - Separate GUI and VJ processes
Avoids pygame/Tkinter conflicts by running them separately
"""
import os
import sys
import subprocess
import time
import signal
import argparse


def start_lighting_gui():
    """Start the lighting system with GUI (no VJ)"""
    print("🎛️ Starting lighting GUI system...")

    # Disable VJ in the director to avoid pygame conflict
    env = os.environ.copy()
    env["PARROT_DISABLE_VJ"] = "1"

    cmd = [
        sys.executable,
        "-m",
        "parrot.main",
        "--no-web",  # Disable web to avoid port conflicts
    ]

    return subprocess.Popen(cmd, env=env)


def start_vj_system():
    """Start the VJ system separately"""
    print("🎬 Starting VJ system...")

    cmd = [
        sys.executable,
        "start_party_parrot.py",
        "--force-headless",
        "--web-port",
        "4041",
    ]

    return subprocess.Popen(cmd)


def main():
    """Run split Party Parrot system"""
    parser = argparse.ArgumentParser(description="Party Parrot Split System")
    parser.add_argument(
        "--lighting-only", action="store_true", help="Run only lighting GUI"
    )
    parser.add_argument("--vj-only", action="store_true", help="Run only VJ system")
    args = parser.parse_args()

    print("🚀" * 50)
    print("  PARTY PARROT SPLIT SYSTEM")
    print("🚀" * 50)

    processes = []

    try:
        if args.lighting_only:
            print("\n🎛️ Running lighting system only...")
            lighting_proc = start_lighting_gui()
            processes.append(lighting_proc)
            print("✅ Lighting GUI started")

        elif args.vj_only:
            print("\n🎬 Running VJ system only...")
            vj_proc = start_vj_system()
            processes.append(vj_proc)
            print("✅ VJ system started")
            print("🌐 VJ control: http://localhost:4041")

        else:
            print("\n🎭 Running both systems separately...")

            # Start lighting GUI
            lighting_proc = start_lighting_gui()
            processes.append(lighting_proc)
            print("✅ Lighting GUI started")

            # Wait a moment
            time.sleep(2)

            # Start VJ system
            vj_proc = start_vj_system()
            processes.append(vj_proc)
            print("✅ VJ system started")

            print("\n🎯 System Status:")
            print("   🎛️ Lighting GUI: Running with full control interface")
            print("   🎬 VJ System: Running with all 70+ interpreters")
            print("   🌐 VJ Control: http://localhost:4041")
            print("   🎆 Both systems operational!")

        print(f"\n⏰ Systems running... Press Ctrl+C to stop")

        # Wait for processes
        while True:
            time.sleep(1)

            # Check if processes are still running
            for i, proc in enumerate(processes):
                if proc.poll() is not None:
                    print(f"⚠️ Process {i} ended with code {proc.returncode}")

    except KeyboardInterrupt:
        print("\n🛑 Stopping Party Parrot systems...")

        # Terminate all processes
        for proc in processes:
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except:
                proc.kill()

        print("✅ All systems stopped")

    except Exception as e:
        print(f"\n❌ Error: {e}")

        # Clean up processes
        for proc in processes:
            try:
                proc.kill()
            except:
                pass


if __name__ == "__main__":
    main()
