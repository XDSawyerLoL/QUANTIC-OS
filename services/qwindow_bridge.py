#!/usr/bin/env python3
"""Quantic Window Bridge.

Conservative compositor/window adapter used by Quantic Desktop V2.
- X11: real enumeration and geometry changes through wmctrl when available.
- Wayland: capability is detected and reported; no unsafe/unverified compositor hacks.

The bridge is intentionally allowlisted to layout operations only. It never executes
arbitrary commands supplied by the agent or UI.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from dataclasses import asdict, dataclass
from typing import Iterable


LAYOUTS = {
    "focus": [(0.08, 0.06, 0.84, 0.86)],
    "half": [(0.02, 0.05, 0.47, 0.88), (0.51, 0.05, 0.47, 0.88)],
    "wide": [(0.02, 0.05, 0.62, 0.88), (0.66, 0.05, 0.32, 0.88)],
    "triple": [(0.02, 0.05, 0.47, 0.88), (0.51, 0.05, 0.225, 0.88), (0.755, 0.05, 0.225, 0.88)],
}


@dataclass(frozen=True)
class Window:
    wid: str
    desktop: int
    pid: int
    x: int
    y: int
    width: int
    height: int
    wm_class: str
    title: str


def _run(args: list[str], timeout: float = 1.5) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False)


def session_type() -> str:
    return os.environ.get("XDG_SESSION_TYPE", "").strip().lower() or ("x11" if os.environ.get("DISPLAY") else "unknown")


def capability() -> dict:
    session = session_type()
    has_wmctrl = shutil.which("wmctrl") is not None
    mode = "x11-wmctrl" if session == "x11" and has_wmctrl else "observe-only"
    return {
        "session": session,
        "mode": mode,
        "can_list": mode == "x11-wmctrl",
        "can_move_resize": mode == "x11-wmctrl",
        "reason": "" if mode == "x11-wmctrl" else ("wmctrl absent" if session == "x11" else "Wayland compositor adapter not enabled"),
    }


def list_windows() -> list[Window]:
    cap = capability()
    if not cap["can_list"]:
        return []
    proc = _run(["wmctrl", "-lpGx"])
    if proc.returncode != 0:
        return []
    windows: list[Window] = []
    for line in proc.stdout.splitlines():
        parts = line.split(None, 9)
        if len(parts) < 10:
            continue
        try:
            wid, desktop, pid, x, y, width, height, _host, wm_class, title = parts
            windows.append(Window(wid, int(desktop), int(pid), int(x), int(y), int(width), int(height), wm_class, title))
        except (ValueError, TypeError):
            continue
    return windows


def _screen_size() -> tuple[int, int]:
    # xrandr is preferred because the shell can span a virtual desktop.
    if shutil.which("xrandr"):
        proc = _run(["xrandr", "--current"])
        for line in proc.stdout.splitlines():
            if " current " in line:
                try:
                    tail = line.split(" current ", 1)[1].split(",", 1)[0]
                    w, h = tail.split(" x ")
                    return int(w), int(h)
                except (ValueError, IndexError):
                    pass
    return (1920, 1080)


def _eligible(windows: Iterable[Window]) -> list[Window]:
    excluded = ("quantic-home", "plasmashell", "ksmserver", "kwin", "desktop")
    result = []
    for window in windows:
        hay = f"{window.wm_class} {window.title}".lower()
        if any(token in hay for token in excluded):
            continue
        if window.width < 120 or window.height < 80:
            continue
        result.append(window)
    return result


def apply_layout(layout_id: str, windows: list[Window] | None = None) -> dict:
    if layout_id not in LAYOUTS:
        return {"ok": False, "error": "unknown-layout", "layout": layout_id}
    cap = capability()
    if not cap["can_move_resize"]:
        return {"ok": False, "error": "unsupported-session", "capability": cap}
    selected = _eligible(windows if windows is not None else list_windows())
    if not selected:
        return {"ok": False, "error": "no-eligible-windows", "capability": cap}
    sw, sh = _screen_size()
    slots = LAYOUTS[layout_id]
    applied = []
    for window, slot in zip(selected, slots):
        rx, ry, rw, rh = slot
        x, y, width, height = int(sw * rx), int(sh * ry), int(sw * rw), int(sh * rh)
        proc = _run(["wmctrl", "-ir", window.wid, "-b", "remove,maximized_vert,maximized_horz"])
        if proc.returncode == 0:
            proc = _run(["wmctrl", "-ir", window.wid, "-e", f"0,{x},{y},{width},{height}"])
        applied.append({"wid": window.wid, "ok": proc.returncode == 0, "geometry": [x, y, width, height]})
    return {
        "ok": bool(applied) and all(item["ok"] for item in applied),
        "layout": layout_id,
        "screen": [sw, sh],
        "applied": applied,
        "remaining": max(0, len(selected) - len(slots)),
        "capability": cap,
    }


def snapshot() -> dict:
    return {"capability": capability(), "windows": [asdict(w) for w in list_windows()]}


def main() -> int:
    parser = argparse.ArgumentParser(description="Quantic compositor/window bridge")
    parser.add_argument("command", choices=("capability", "list", "snapshot", "apply"))
    parser.add_argument("layout", nargs="?", choices=tuple(LAYOUTS))
    args = parser.parse_args()
    if args.command == "capability":
        payload = capability()
    elif args.command == "list":
        payload = [asdict(w) for w in list_windows()]
    elif args.command == "snapshot":
        payload = snapshot()
    else:
        if not args.layout:
            parser.error("apply requires a layout")
        payload = apply_layout(args.layout)
    print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    return 0 if not isinstance(payload, dict) or payload.get("ok", True) else 2


if __name__ == "__main__":
    raise SystemExit(main())
