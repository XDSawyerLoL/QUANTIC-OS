#!/usr/bin/env python3
"""Persistent AURA Everywhere presence for Quantic OS.

This daemon exposes only operational product presence. It never forwards files,
user activity, prompts, identity material or message content.
"""
from __future__ import annotations

import signal
import time

from aura_bridge import observe, register

INTERVAL_SECONDS = 300
_running = True


def _stop(_signum, _frame) -> None:
    global _running
    _running = False


def main() -> int:
    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    register()
    observe(
        "online",
        "Quantic OS actif et relié à AURA Everywhere.",
        {
            "bridge_version": "aura-universal-bridge-v1",
            "presence_daemon": True,
            "content_forwarded": False,
        },
    )

    while _running:
        deadline = time.monotonic() + INTERVAL_SECONDS
        while _running and time.monotonic() < deadline:
            time.sleep(min(1.0, max(0.0, deadline - time.monotonic())))
        if not _running:
            break
        observe(
            "online",
            "Quantic OS heartbeat.",
            {
                "presence_daemon": True,
                "content_forwarded": False,
            },
        )

    observe(
        "offline",
        "Arrêt propre du heartbeat Quantic OS.",
        {
            "presence_daemon": True,
            "content_forwarded": False,
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
