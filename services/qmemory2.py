#!/usr/bin/env python3
"""Q-Memory 2: local-first durable memory with provenance and hybrid recall.

The base implementation intentionally uses only Python's standard library so it
is available in the live OS. SQLite FTS provides lexical retrieval while a
small deterministic hashed-vector layer provides dependency-free semantic
ranking until an optional embedding backend is present.
"""
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any, Iterable
import hashlib
import json
import math
import re
import sqlite3
import time

try:
    from .qcontracts import MemoryRecord
except ImportError:
    from qcontracts import MemoryRecord

DEFAULT_DB = Path("/var/lib/quantic/memory/qmemory2.sqlite3")
TOKEN_RE = re.compile(r"[\wÀ-ÿ'-]+", re.UNICODE)
VECTOR_DIMS = 192


def _tokens(text: str) -> list[str]:
    return [x.lower() for x in TOKEN_RE.findall(text)]


def _vector(text: str) -> list[float]:
    vec = [0.0] * VECTOR_DIMS
    for token in _tokens(text):
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
        raw = int.from_bytes(digest, "big")
        index = raw % VECTOR_DIMS
        sign = -1.0 if raw & 1 else 1.0
        vec[index] += sign
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / norm for x in vec]


def _cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def _text(content: dict[str, Any]) -> str:
    parts: list[str] = []
    for key, value in content.items():
        if isinstance(value, (str, int, float, bool)):
            parts.append(f"{key} {value}")
        elif isinstance(value, list):
            parts.extend(str(x) for x in value)
    return " ".join(parts)


class MemoryStore:
    def __init__(self, path: Path = DEFAULT_DB) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path)
        self.db.row_factory = sqlite3.Row
        self._init()

    def _init(self) -> None:
        self.db.executescript(
            """
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                namespace TEXT NOT NULL,
                kind TEXT NOT NULL,
                content_json TEXT NOT NULL,
                provenance_json TEXT NOT NULL,
                confidence REAL NOT NULL,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                last_accessed REAL NOT NULL,
                access_count INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'active',
                supersedes_id TEXT,
                vector_json TEXT NOT NULL,
                search_text TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_mem_ns_kind ON memories(namespace, kind, status);
            CREATE INDEX IF NOT EXISTS idx_mem_updated ON memories(updated_at DESC);
            """
        )
        try:
            self.db.execute("CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(id UNINDEXED, search_text)")
            self.fts = True
        except sqlite3.OperationalError:
            self.fts = False
        self.db.commit()

    def close(self) -> None:
        self.db.close()

    def remember(self, record: MemoryRecord, *, supersedes_id: str | None = None) -> MemoryRecord:
        if not 0.0 <= record.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        now = time.time()
        text = _text(record.content)
        vec = _vector(text)
        with self.db:
            if supersedes_id:
                self.db.execute("UPDATE memories SET status='superseded', updated_at=? WHERE id=?", (now, supersedes_id))
            self.db.execute(
                """INSERT OR REPLACE INTO memories
                (id,namespace,kind,content_json,provenance_json,confidence,created_at,updated_at,last_accessed,access_count,status,supersedes_id,vector_json,search_text)
                VALUES (?,?,?,?,?,?,?,?,?,0,'active',?,?,?)""",
                (
                    record.id, record.namespace, record.kind,
                    json.dumps(record.content, ensure_ascii=False, sort_keys=True),
                    json.dumps(record.provenance, ensure_ascii=False, sort_keys=True),
                    record.confidence, record.created_at, now, now, supersedes_id,
                    json.dumps(vec), text,
                ),
            )
            if self.fts:
                self.db.execute("DELETE FROM memory_fts WHERE id=?", (record.id,))
                self.db.execute("INSERT INTO memory_fts(id,search_text) VALUES (?,?)", (record.id, text))
        return record

    def get(self, memory_id: str, *, touch: bool = True) -> dict[str, Any] | None:
        row = self.db.execute("SELECT * FROM memories WHERE id=?", (memory_id,)).fetchone()
        if row is None:
            return None
        if touch:
            with self.db:
                self.db.execute(
                    "UPDATE memories SET last_accessed=?, access_count=access_count+1 WHERE id=?",
                    (time.time(), memory_id),
                )
        return self._decode(row)

    def forget(self, memory_id: str) -> bool:
        with self.db:
            cur = self.db.execute("UPDATE memories SET status='forgotten', updated_at=? WHERE id=?", (time.time(), memory_id))
            if self.fts:
                self.db.execute("DELETE FROM memory_fts WHERE id=?", (memory_id,))
        return cur.rowcount > 0

    def delete(self, memory_id: str) -> bool:
        with self.db:
            cur = self.db.execute("DELETE FROM memories WHERE id=?", (memory_id,))
            if self.fts:
                self.db.execute("DELETE FROM memory_fts WHERE id=?", (memory_id,))
        return cur.rowcount > 0

    def recall(self, query: str, *, namespace: str | None = None, kinds: Iterable[str] | None = None, limit: int = 8) -> list[dict[str, Any]]:
        if limit <= 0:
            return []
        clauses = ["status='active'"]
        args: list[Any] = []
        if namespace is not None:
            clauses.append("namespace=?")
            args.append(namespace)
        kinds_list = list(kinds or [])
        if kinds_list:
            clauses.append("kind IN (%s)" % ",".join("?" for _ in kinds_list))
            args.extend(kinds_list)
        rows = self.db.execute(
            f"SELECT * FROM memories WHERE {' AND '.join(clauses)} ORDER BY updated_at DESC LIMIT 500",
            args,
        ).fetchall()
        qvec = _vector(query)
        qtokens = set(_tokens(query))
        now = time.time()
        scored: list[tuple[float, sqlite3.Row]] = []
        for row in rows:
            text_tokens = set(_tokens(row["search_text"]))
            lexical = len(qtokens & text_tokens) / max(1, len(qtokens))
            semantic = max(0.0, _cosine(qvec, json.loads(row["vector_json"])))
            age_days = max(0.0, now - float(row["updated_at"])) / 86400.0
            recency = 1.0 / (1.0 + age_days / 30.0)
            confidence = float(row["confidence"])
            score = 0.48 * lexical + 0.32 * semantic + 0.12 * confidence + 0.08 * recency
            if score > 0.05:
                scored.append((score, row))
        scored.sort(key=lambda x: x[0], reverse=True)
        out: list[dict[str, Any]] = []
        for score, row in scored[:limit]:
            item = self._decode(row)
            item["score"] = round(score, 6)
            out.append(item)
            with self.db:
                self.db.execute("UPDATE memories SET last_accessed=?, access_count=access_count+1 WHERE id=?", (now, row["id"]))
        return out

    def find_conflicts(self, record: MemoryRecord, *, key: str = "key") -> list[dict[str, Any]]:
        marker = record.content.get(key)
        if marker is None:
            return []
        rows = self.db.execute(
            "SELECT * FROM memories WHERE namespace=? AND kind=? AND status='active' AND id<>?",
            (record.namespace, record.kind, record.id),
        ).fetchall()
        conflicts: list[dict[str, Any]] = []
        for row in rows:
            item = self._decode(row)
            if item["content"].get(key) == marker and item["content"] != record.content:
                conflicts.append(item)
        return conflicts

    def decay_candidates(self, *, older_than_days: int = 90, max_confidence: float = 0.45, limit: int = 100) -> list[dict[str, Any]]:
        cutoff = time.time() - older_than_days * 86400
        rows = self.db.execute(
            """SELECT * FROM memories WHERE status='active' AND confidence<=? AND last_accessed<?
               ORDER BY last_accessed ASC LIMIT ?""",
            (max_confidence, cutoff, limit),
        ).fetchall()
        return [self._decode(x) for x in rows]

    def export_namespace(self, namespace: str) -> list[dict[str, Any]]:
        rows = self.db.execute(
            "SELECT * FROM memories WHERE namespace=? ORDER BY created_at ASC", (namespace,)
        ).fetchall()
        return [self._decode(x) for x in rows]

    @staticmethod
    def _decode(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "namespace": row["namespace"],
            "kind": row["kind"],
            "content": json.loads(row["content_json"]),
            "provenance": json.loads(row["provenance_json"]),
            "confidence": float(row["confidence"]),
            "created_at": float(row["created_at"]),
            "updated_at": float(row["updated_at"]),
            "last_accessed": float(row["last_accessed"]),
            "access_count": int(row["access_count"]),
            "status": row["status"],
            "supersedes_id": row["supersedes_id"],
        }
