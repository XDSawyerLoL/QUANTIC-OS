#!/usr/bin/env python3
"""Quantic Window Bridge.

Conservative compositor/window adapter used by Quantic Desktop V2.
- X11: real enumeration, exact Mission snapshots and geometry restore through wmctrl.
- Plasma Wayland: one-shot KWin 6 scripts loaded through KWin's public D-Bus
  scripting interface for allowlisted Q-Snap layouts.

Mission snapshots never accept arbitrary filesystem paths. A bounded state id is
resolved under Quantic's private state directory.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


LAYOUTS = {
    "focus": [(0.08, 0.06, 0.84, 0.86)],
    "half": [(0.02, 0.05, 0.47, 0.88), (0.51, 0.05, 0.47, 0.88)],
    "wide": [(0.02, 0.05, 0.62, 0.88), (0.66, 0.05, 0.32, 0.88)],
    "triple": [(0.02, 0.05, 0.47, 0.88), (0.51, 0.05, 0.225, 0.88), (0.755, 0.05, 0.225, 0.88)],
}
STATE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


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


@dataclass(frozen=True)
class Output:
    name: str
    x: int
    y: int
    width: int
    height: int


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
        "can_exact_snapshot": mode == "x11-wmctrl",
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


def list_outputs() -> list[Output]:
    if not shutil.which("xrandr"):
        sw, sh = _screen_size()
        return [Output("default", 0, 0, sw, sh)]
    proc = _run(["xrandr", "--current"])
    outputs: list[Output] = []
    geometry_re = re.compile(r"\b(\d+)x(\d+)\+(-?\d+)\+(-?\d+)\b")
    for line in proc.stdout.splitlines():
        if " connected" not in line:
            continue
        match = geometry_re.search(line)
        if not match:
            continue
        name = line.split(None, 1)[0]
        width, height, x, y = map(int, match.groups())
        if width > 0 and height > 0:
            outputs.append(Output(name, x, y, width, height))
    if outputs:
        return outputs
    sw, sh = _screen_size()
    return [Output("default", 0, 0, sw, sh)]


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


def _output_for_window(window: Window, outputs: list[Output]) -> Output:
    cx = window.x + window.width / 2
    cy = window.y + window.height / 2
    for output in outputs:
        if output.x <= cx < output.x + output.width and output.y <= cy < output.y + output.height:
            return output
    return min(outputs, key=lambda o: abs(cx - (o.x + o.width / 2)) + abs(cy - (o.y + o.height / 2)))


def _state_root() -> Path:
    override = os.environ.get("QUANTIC_WINDOW_STATE_DIR", "").strip()
    root = Path(override).expanduser() if override else Path.home() / ".local" / "state" / "quantic" / "windows"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _state_path(state_id: str) -> Path:
    if not STATE_ID_RE.fullmatch(state_id):
        raise ValueError("invalid-state-id")
    return _state_root() / f"{state_id}.json"


def _atomic_json(path: Path, payload: dict) -> None:
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass


def capture_state(state_id: str) -> dict:
    try:
        path = _state_path(state_id)
    except ValueError:
        return {"ok": False, "error": "invalid-state-id"}
    cap = capability()
    if not cap["can_exact_snapshot"]:
        return {"ok": False, "error": "exact-snapshot-unsupported", "capability": cap}
    outputs = list_outputs()
    windows = _eligible(list_windows())
    entries = []
    for window in windows:
        output = _output_for_window(window, outputs)
        nx = (window.x - output.x) / max(1, output.width)
        ny = (window.y - output.y) / max(1, output.height)
        nw = window.width / max(1, output.width)
        nh = window.height / max(1, output.height)
        entries.append({
            "wm_class": window.wm_class,
            "title": window.title,
            "desktop": window.desktop,
            "output": output.name,
            "geometry": [window.x, window.y, window.width, window.height],
            "normalized": [round(nx, 6), round(ny, 6), round(nw, 6), round(nh, 6)],
        })
    payload = {
        "version": 1,
        "state_id": state_id,
        "session": cap["mode"],
        "outputs": [asdict(o) for o in outputs],
        "windows": entries,
    }
    _atomic_json(path, payload)
    return {"ok": True, "state_id": state_id, "windows": len(entries), "outputs": len(outputs)}


def _score_match(saved: dict, current: Window) -> int:
    score = 0
    if saved.get("wm_class", "").lower() == current.wm_class.lower():
        score += 100
    saved_title = saved.get("title", "").strip().lower()
    current_title = current.title.strip().lower()
    if saved_title and current_title:
        if saved_title == current_title:
            score += 40
        elif saved_title in current_title or current_title in saved_title:
            score += 15
    if saved.get("desktop") == current.desktop:
        score += 3
    return score


def restore_state(state_id: str) -> dict:
    try:
        path = _state_path(state_id)
    except ValueError:
        return {"ok": False, "error": "invalid-state-id"}
    cap = capability()
    if not cap["can_exact_snapshot"]:
        return {"ok": False, "error": "exact-restore-unsupported", "capability": cap}
    if not path.exists():
        return {"ok": False, "error": "state-not-found"}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"ok": False, "error": "state-invalid"}
    if payload.get("version") != 1 or not isinstance(payload.get("windows"), list):
        return {"ok": False, "error": "state-version-unsupported"}
    outputs = list_outputs()
    by_name = {o.name: o for o in outputs}
    current = _eligible(list_windows())
    available = list(range(len(current)))
    restored = []
    for saved in payload["windows"]:
        ranked = sorted((( _score_match(saved, current[i]), i) for i in available), reverse=True)
        if not ranked or ranked[0][0] < 100:
            restored.append({"ok": False, "error": "window-not-found", "wm_class": saved.get("wm_class", "")})
            continue
        _, idx = ranked[0]
        available.remove(idx)
        window = current[idx]
        output = by_name.get(saved.get("output"))
        if output is None:
            old_outputs = payload.get("outputs", [])
            old_index = next((i for i, o in enumerate(old_outputs) if o.get("name") == saved.get("output")), 0)
            output = outputs[min(old_index, len(outputs) - 1)]
        norm = saved.get("normalized", [])
        if not (isinstance(norm, list) and len(norm) == 4):
            restored.append({"ok": False, "error": "invalid-geometry", "wm_class": window.wm_class})
            continue
        nx, ny, nw, nh = [float(v) for v in norm]
        width = max(160, min(output.width, round(output.width * nw)))
        height = max(100, min(output.height, round(output.height * nh)))
        x = round(output.x + output.width * nx)
        y = round(output.y + output.height * ny)
        x = max(output.x, min(x, output.x + output.width - width))
        y = max(output.y, min(y, output.y + output.height - height))
        _run(["wmctrl", "-ir", window.wid, "-b", "remove,maximized_vert,maximized_horz,fullscreen"])
        desktop = int(saved.get("desktop", window.desktop))
        if desktop >= 0:
            _run(["wmctrl", "-ir", window.wid, "-t", str(desktop)])
        proc = _run(["wmctrl", "-ir", window.wid, "-e", f"0,{x},{y},{width},{height}"])
        restored.append({"ok": proc.returncode == 0, "wid": window.wid, "output": output.name, "geometry": [x, y, width, height]})
    successful = sum(1 for item in restored if item.get("ok"))
    return {
        "ok": successful > 0 and successful == len(restored),
        "state_id": state_id,
        "restored": successful,
        "requested": len(payload["windows"]),
        "results": restored,
        "topology_changed": [o.get("name") for o in payload.get("outputs", [])] != [o.name for o in outputs],
    }


def _kwin_script(layout_id: str) -> str:
    slots = json.dumps(LAYOUTS[layout_id], separators=(",", ":"))
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
    const w = wins[i]; const s = slots[i];
    w.fullScreen = false; w.minimized = false;
    w.frameGeometry = {{
        x: Math.round(area.x + area.width * s[0]), y: Math.round(area.y + area.height * s[1]),
        width: Math.round(area.width * s[2]), height: Math.round(area.height * s[3])
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
            handle.write(_kwin_script(layout_id)); path = handle.name
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
        return {"ok": run.returncode == 0, "layout": layout_id, "mode": "wayland-kwin6", "script_id": script_id,
                "error": "" if run.returncode == 0 else "kwin-run-failed"}
    except (OSError, subprocess.SubprocessError) as exc:
        return {"ok": False, "error": "kwin-execution-failed", "detail": str(exc)[:240]}
    finally:
        if path:
            try: os.unlink(path)
            except OSError: pass


def apply_layout(layout_id: str, windows: list[Window] | None = None) -> dict:
    if layout_id not in LAYOUTS:
        return {"ok": False, "error": "unknown-layout", "layout": layout_id}
    cap = capability()
    if not cap["can_move_resize"]:
        return {"ok": False, "error": "unsupported-session", "capability": cap}
    if cap["mode"] == "wayland-kwin6":
        result = _apply_kwin(layout_id); result["capability"] = cap; return result
    selected = _eligible(windows if windows is not None else list_windows())
    if not selected:
        return {"ok": False, "error": "no-eligible-windows", "capability": cap}
    sw, sh = _screen_size(); slots = LAYOUTS[layout_id]; applied = []
    for window, slot in zip(selected, slots):
        rx, ry, rw, rh = slot
        x, y, width, height = int(sw * rx), int(sh * ry), int(sw * rw), int(sh * rh)
        proc = _run(["wmctrl", "-ir", window.wid, "-b", "remove,maximized_vert,maximized_horz"])
        if proc.returncode == 0:
            proc = _run(["wmctrl", "-ir", window.wid, "-e", f"0,{x},{y},{width},{height}"])
        applied.append({"wid": window.wid, "ok": proc.returncode == 0, "geometry": [x, y, width, height]})
    return {"ok": bool(applied) and all(item["ok"] for item in applied), "layout": layout_id, "screen": [sw, sh],
            "applied": applied, "remaining": max(0, len(selected) - len(slots)), "capability": cap}


def snapshot() -> dict:
    return {"capability": capability(), "outputs": [asdict(o) for o in list_outputs()], "windows": [asdict(w) for w in list_windows()]}


def main() -> int:
    parser = argparse.ArgumentParser(description="Quantic compositor/window bridge")
    parser.add_argument("command", choices=("capability", "list", "snapshot", "apply", "capture-state", "restore-state"))
    parser.add_argument("argument", nargs="?")
    args = parser.parse_args()
    if args.command == "capability": payload = capability()
    elif args.command == "list": payload = [asdict(w) for w in list_windows()]
    elif args.command == "snapshot": payload = snapshot()
    elif args.command == "capture-state": payload = capture_state(args.argument or "")
    elif args.command == "restore-state": payload = restore_state(args.argument or "")
    else:
        if not args.argument: parser.error("apply requires a layout")
        payload = apply_layout(args.argument)
    print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    return 0 if not isinstance(payload, dict) or payload.get("ok", True) else 2


if __name__ == "__main__":
    raise SystemExit(main())
