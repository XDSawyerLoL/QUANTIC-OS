#!/usr/bin/env python3
"""Quantic Window Bridge.

Conservative compositor/window adapter used by Quantic Desktop V2.
- X11: real enumeration and geometry changes through wmctrl when available.
- Plasma Wayland: one-shot KWin 6 scripts loaded through KWin's public D-Bus
  scripting interface. No shell command supplied by the agent is ever executed.

The bridge is intentionally allowlisted to known layout operations only.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
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


def _qdbus() -> str | None:
    return shutil.which("qdbus6") or shutil.which("qdbus")


def _kwin_available(qdbus: str | None = None) -> bool:
    exe = qdbus or _qdbus()
    if not exe:
        return False
    try:
        proc = _run([exe, "org.kde.KWin", "/Scripting"], timeout=1.0)
    except (OSError, subprocess.SubprocessError):
        return False
    return proc.returncode == 0 and "loadScript" in (proc.stdout + proc.stderr)


def capability() -> dict:
    session = session_type()
    has_wmctrl = shutil.which("wmctrl") is not None
    qdbus = _qdbus()
    has_kwin = session == "wayland" and _kwin_available(qdbus)
    if session == "x11" and has_wmctrl:
        mode = "x11-wmctrl"
    elif has_kwin:
        mode = "wayland-kwin6"
    else:
        mode = "observe-only"
    return {
        "session": session,
        "mode": mode,
        "can_list": mode == "x11-wmctrl",
        "can_move_resize": mode in {"x11-wmctrl", "wayland-kwin6"},
        "reason": "" if mode != "observe-only" else (
            "wmctrl absent" if session == "x11" else
            "KWin scripting D-Bus unavailable" if session == "wayland" else
            "unsupported session"
        ),
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


def _kwin_script(layout_id: str) -> str:
    slots = json.dumps(LAYOUTS[layout_id], separators=(",", ":"))
    # The script only touches ordinary, managed, movable/resizable windows.
    # It uses KWin's active output client area, so panels and screen geometry are respected.
    return f'''(function() {{
const slots = {slots};
const wins = workspace.stackingOrder.filter(function(w) {{
    return w && w.managed && !w.deleted && !w.specialWindow && !w.skipTaskbar &&
           w.moveable && w.resizeable && w.desktopFileName !== "quantic-home";
}}).reverse();
const output = workspace.activeScreen;
const desktop = workspace.currentDesktop;
const area = clientArea(KWin.MaximizeArea, output, desktop);
for (let i = 0; i < Math.min(wins.length, slots.length); ++i) {{
    const w = wins[i];
    const s = slots[i];
    w.fullScreen = false;
    w.minimized = false;
    w.frameGeometry = {{
        x: Math.round(area.x + area.width * s[0]),
        y: Math.round(area.y + area.height * s[1]),
        width: Math.round(area.width * s[2]),
        height: Math.round(area.height * s[3])
    }};
}}
}})();
'''


def _apply_kwin(layout_id: str) -> dict:
    qdbus = _qdbus()
    if not qdbus or not _kwin_available(qdbus):
        return {"ok": False, "error": "kwin-scripting-unavailable"}
    plugin = f"quantic-layout-{os.getpid()}"
    path = ""
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".js", prefix="quantic-kwin-", delete=False, encoding="utf-8") as handle:
            handle.write(_kwin_script(layout_id))
            path = handle.name
        loaded = _run([qdbus, "org.kde.KWin", "/Scripting", "org.kde.kwin.Scripting.loadScript", path, plugin], timeout=2.0)
        if loaded.returncode != 0:
            return {"ok": False, "error": "kwin-load-failed", "detail": loaded.stderr.strip()[:240]}
        raw = loaded.stdout.strip().splitlines()[-1] if loaded.stdout.strip() else ""
        try:
            script_id = int(raw)
        except ValueError:
            return {"ok": False, "error": "kwin-invalid-script-id", "detail": raw[:80]}
        if script_id < 0:
            return {"ok": False, "error": "kwin-load-refused"}
        run = _run([qdbus, "org.kde.KWin", f"/{script_id}", "org.kde.kwin.Scripting.run"], timeout=2.0)
        _run([qdbus, "org.kde.KWin", "/Scripting", "org.kde.kwin.Scripting.unloadScript", plugin], timeout=1.0)
        return {
            "ok": run.returncode == 0,
            "layout": layout_id,
            "mode": "wayland-kwin6",
            "script_id": script_id,
            "error": "" if run.returncode == 0 else "kwin-run-failed",
        }
    except (OSError, subprocess.SubprocessError) as exc:
        return {"ok": False, "error": "kwin-execution-failed", "detail": str(exc)[:240]}
    finally:
        if path:
            try:
                os.unlink(path)
            except OSError:
                pass


def apply_layout(layout_id: str, windows: list[Window] | None = None) -> dict:
    if layout_id not in LAYOUTS:
        return {"ok": False, "error": "unknown-layout", "layout": layout_id}
    cap = capability()
    if not cap["can_move_resize"]:
        return {"ok": False, "error": "unsupported-session", "capability": cap}
    if cap["mode"] == "wayland-kwin6":
        result = _apply_kwin(layout_id)
        result["capability"] = cap
        return result
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
