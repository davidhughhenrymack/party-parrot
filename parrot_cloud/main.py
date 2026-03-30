from __future__ import annotations

import argparse
import socket

from parrot_cloud.app import create_app
from parrot_cloud.management import build_frontend, initialize_database


def get_local_ip() -> str:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 1))
        local_ip = sock.getsockname()[0]
        sock.close()
        return local_ip
    except Exception:
        return "127.0.0.1"


def parse_args():
    parser = argparse.ArgumentParser(description="Party Parrot cloud service")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=4041)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    initialize_database()
    build_frontend()
    app = create_app()
    local_ip = get_local_ip()
    print(f"\n☁️  Parrot Cloud available at: http://{local_ip}:{args.port}/")
    print(f"🗄️  Parrot Cloud database is local and auto-seeded on first launch\n")
    app.run(host=args.host, port=args.port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
