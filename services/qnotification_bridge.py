#!/usr/bin/env python3
"""Read-only notification projection for Quantic Desktop.

Turns the durable Q-EventBus JSONL journal into a small, sanitized notification feed.
The shell never executes event payloads; it only displays bounded text fields.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import time
from pathlib import Path
from typing import Any

DEFAULT_JOURNAL = Path("/var/lib/quantic/events/events.jsonl")
DEFAULT_STATE = Path.home() / ".local" / "state" / "quantic" / "notifications.json"
MAX_ITEMS = 40
MAX_TEXT = 280
SECRET_RE = re.compile(r"(?i)(api[_-]?key|token|authorization|password|secret)\s*[:=]\s*[^\s,;]+")


def _journal() -> Path:
    return Path(os.environ.get("QUANTIC_EVENT_JOURNAL", str(DEFAULT_JOURNAL)))


def _state_path() -> Path:
    return Path(os.environ.get("QUANTIC_NOTIFICATION_STATE", str(DEFAULT_STATE))).expanduser()


def _safe_text(value: Any, limit: int = MAX_TEXT) -> str:
    text = str(value or "").replace("\x00", " ").replace("\r", " ").strip()
    text = SECRET_RE.sub(lambda m: f"{m.group(1)}=[redacted]", text)
    text = " ".join(text.split())
    return text[:limit]


def _read_state() -> dict[str, Any]:
    path = _state_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _write_state(data: dict[str, Any]) -> None:
    path = _state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    os.replace(tmp, path)


def _severity(topic: str, payload: dict[str, Any]) -> str:
    explicit = _safe_text(payload.get("severity", ""), 16).lower()
    if explicit in {"info", "success", "warning", "critical"}:
        return explicit
    hay = f"{topic} {_safe_text(payload.get('status', ''), 60)}".lower()
    if any(k in hay for k in ("critical", "security.denied", "rollback.failed", "health.critical")):
        return "critical"
    if any(k in hay for k in ("warning", "failed", "error", "approval", "rollback")):
        return "warning"
    if any(k in hay for k in ("success", "verified", "completed", "done")):
        return "success"
    return "info"


def _title(topic: str, payload: dict[str, Any], source: str) -> str:
    custom = _safe_text(payload.get("title", ""), 80)
    if custom:
        return custom
    if topic.startswith("security") or topic.startswith("policy"):
        return "Sécurité"
    if topic.startswith("mission") or topic.startswith("desktop"):
        return "Mission"
    if topic.startswith("agent") or topic.startswith("plan") or topic.startswith("task"):
        return "Quantic"
    if topic.startswith("health") or topic.startswith("resource"):
        return "Système"
    return _safe_text(source or "Quantic", 80) or "Quantic"


def _message(topic: str, payload: dict[str, Any]) -> str:
    for key in ("message", "detail", "summary", "reason", "result", "status"):
        if key in payload:
            text = _safe_text(payload.get(key))
            if text:
                return text
    compact = []
    for key, value in payload.items():
        if key.lower() in {"token", "api_key", "apikey", "authorization", "password", "secret"}:
            continue
        if isinstance(value, (str, int, float, bool)):
            compact.append(f"{_safe_text(key, 30)}: {_safe_text(value, 90)}")
        if len(compact) >= 3:
            break
    return _safe_text(" · ".join(compact) or topic)


def recent(limit: int = 20) -> dict[str, Any]:
    limit = max(1, min(int(limit), MAX_ITEMS))
    journal = _journal()
    state = _read_state()
    cleared_at = float(state.get("cleared_at", 0) or 0)
    rows: list[dict[str, Any]] = []
    if journal.exists():
        try:
            lines = journal.read_text(encoding="utf-8", errors="replace").splitlines()[-400:]
        except OSError:
            lines = []
        for line in lines:
            try:
                raw = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(raw, dict):
                continue
            try:
                ts = float(raw.get("ts", 0) or 0)
            except (TypeError, ValueError):
                ts = 0
            if ts <= cleared_at:
                continue
            payload = raw.get("payload") if isinstance(raw.get("payload"), dict) else {}
            topic = _safe_text(raw.get("topic", "event"), 100)
            source = _safe_text(raw.get("source", "Quantic"), 80)
            rows.append({
                "id": _safe_text(raw.get("id", f"event-{len(rows)}"), 120),
                "title": _title(topic, payload, source),
                "message": _message(topic, payload),
                "topic": topic,
                "source": source,
                "severity": _severity(topic, payload),
                "ts": ts,
            })
    rows.sort(key=lambda item: item["ts"], reverse=True)
    items = rows[:limit]
    return {"ok": True, "items": items, "count": len(items), "cleared_at": cleared_at}


def clear() -> dict[str, Any]:
    now = time.time()
    _write_state({"cleared_at": now})
    return {"ok": True, "cleared_at": now}


def main() -> int:
    parser = argparse.ArgumentParser(description="Quantic notification projection")
    parser.add_argument("command", choices=("recent", "clear"))
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()
    payload = recent(args.limit) if args.command == "recent" else clear()
    print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    return 0 if payload.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
