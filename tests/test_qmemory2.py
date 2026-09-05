from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SERVICES = ROOT / "services"
if str(SERVICES) not in sys.path:
    sys.path.insert(0, str(SERVICES))

from qcontracts import MemoryRecord
from qmemory2 import MemoryStore


def test_remember_and_recall_by_namespace(tmp_path):
    store = MemoryStore(tmp_path / "memory.sqlite3")
    try:
        a = MemoryRecord(
            namespace="project:quantic",
            kind="semantic",
            content={"key": "boot_target", "value": "live usb", "note": "boot from removable media"},
            provenance={"source": "test"},
            confidence=0.95,
        )
        b = MemoryRecord(
            namespace="project:other",
            kind="semantic",
            content={"key": "boot_target", "value": "cloud"},
            provenance={"source": "test"},
            confidence=0.95,
        )
        store.remember(a)
        store.remember(b)
        rows = store.recall("removable live usb boot", namespace="project:quantic")
        assert rows
        assert rows[0]["id"] == a.id
        assert all(x["namespace"] == "project:quantic" for x in rows)
    finally:
        store.close()


def test_supersession_and_conflict_detection(tmp_path):
    store = MemoryStore(tmp_path / "memory.sqlite3")
    try:
        old = MemoryRecord(
            namespace="user",
            kind="semantic",
            content={"key": "preferred_voice", "value": "voice-a"},
            provenance={"source": "user"},
        )
        new = MemoryRecord(
            namespace="user",
            kind="semantic",
            content={"key": "preferred_voice", "value": "voice-b"},
            provenance={"source": "user"},
        )
        store.remember(old)
        conflicts = store.find_conflicts(new)
        assert conflicts and conflicts[0]["id"] == old.id
        store.remember(new, supersedes_id=old.id)
        assert store.get(old.id, touch=False)["status"] == "superseded"
        assert store.get(new.id, touch=False)["status"] == "active"
    finally:
        store.close()


def test_forget_delete_and_export(tmp_path):
    store = MemoryStore(tmp_path / "memory.sqlite3")
    try:
        record = MemoryRecord(
            namespace="session:test",
            kind="episodic",
            content={"event": "hello"},
            provenance={"source": "test"},
            confidence=0.4,
        )
        store.remember(record)
        assert store.export_namespace("session:test")
        assert store.forget(record.id)
        assert store.get(record.id, touch=False)["status"] == "forgotten"
        assert store.delete(record.id)
        assert store.get(record.id, touch=False) is None
    finally:
        store.close()
