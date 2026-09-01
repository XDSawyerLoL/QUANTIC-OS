#!/usr/bin/env python3
"""Durable local event bus for Quantic V2.

The JSONL journal is append-only and dependency-free so it works in the live OS
before any optional database or vector stack is available.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable
import json
import time
import uuid

DEFAULT_JOURNAL = Path("/var/lib/quantic/events/events.jsonl")


@dataclass(frozen=True)
class Event:
    topic: str
    payload: dict[str, Any]
    source: str
    correlation_id: str | None = None
    id: str = field(default_factory=lambda: f"evt_{uuid.uuid4().hex}")
    ts: float = field(default_factory=time.time)


class EventBus:
    def __init__(self, journal: Path = DEFAULT_JOURNAL) -> None:
        self.journal = journal
        self._subscribers: dict[str, list[Callable[[Event], None]]] = {}

    def subscribe(self, topic: str, handler: Callable[[Event], None]) -> None:
        self._subscribers.setdefault(topic, []).append(handler)

    def publish(self, event: Event, *, persist: bool = True) -> Event:
        if persist:
            self.journal.parent.mkdir(parents=True, exist_ok=True)
            with self.journal.open("a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(event), ensure_ascii=False, separators=(",", ":")) + "\n")
        for key in (event.topic, "*"):
            for handler in tuple(self._subscribers.get(key, ())):
                handler(event)
        return event

    def emit(self, topic: str, payload: dict[str, Any], source: str, correlation_id: str | None = None) -> Event:
        return self.publish(Event(topic=topic, payload=payload, source=source, correlation_id=correlation_id))

    def replay(self, *, topic: str | None = None, correlation_id: str | None = None) -> Iterable[Event]:
        if not self.journal.exists():
            return []
        out: list[Event] = []
        with self.journal.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                    event = Event(**row)
                except (json.JSONDecodeError, TypeError, KeyError):
                    continue
                if topic is not None and event.topic != topic:
                    continue
                if correlation_id is not None and event.correlation_id != correlation_id:
                    continue
                out.append(event)
        return out
