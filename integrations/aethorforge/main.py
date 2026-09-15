#!/usr/bin/env python3
import os

from .server import run_server


if __name__ == "__main__":
    run_server(
        host=os.getenv("AETHORFORGE_HOST", "127.0.0.1"),
        port=int(os.getenv("AETHORFORGE_PORT", "8080")),
    )