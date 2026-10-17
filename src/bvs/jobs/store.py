"""Transactional SQLite job state; worker processes never write this database."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

from bvs.errors import BVSError

TERMINAL = {"succeeded", "failed", "cancelled", "interrupted"}
TRANSITIONS = {
    "queued": {"running", "cancelled"},
    "running": {"succeeded", "failed", "cancelling", "interrupted"},
    "cancelling": {"cancelled", "interrupted"},
}


def now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def canonical(value: Any) -> str:
    return json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    )


class Store:
    def __init__(self, directory: Path):
        self.directory = directory
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.path = directory / "jobs.sqlite3"
        with self.connection() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS jobs (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT UNIQUE NOT NULL,
                    kind TEXT NOT NULL, state TEXT NOT NULL, request TEXT NOT NULL,
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL, record TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS idempotency (
                    route TEXT NOT NULL, key TEXT NOT NULL, hash TEXT NOT NULL,
                    job_id TEXT NOT NULL, deleted_at TEXT, PRIMARY KEY(route,key));
                CREATE TABLE IF NOT EXISTS artifacts (
                    id TEXT PRIMARY KEY, job_id TEXT REFERENCES jobs(id), record TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS uploads (id TEXT PRIMARY KEY, record TEXT NOT NULL);
            """)

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try:
            with db:
                yield db
        finally:
            db.close()

    def create(
        self,
        kind: str,
        payload: dict[str, Any],
        *,
        key: str | None = None,
        parent_job_id: str | None = None,
        snapshot: dict[str, Any] | None = None,
        route: str | None = None,
    ) -> dict[str, Any]:
        route = route or kind
        if key is not None and not re.fullmatch(r"[\x20-\x7e]{1,128}", key):
            raise BVSError(
                "INVALID_INPUT", "Idempotency-Key must contain 1–128 printable ASCII characters"
            )
        request = canonical(payload)
        digest = hashlib.sha256(request.encode()).hexdigest()
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            if key:
                old = db.execute(
                    "SELECT * FROM idempotency WHERE route=? AND key=?", (route, key)
                ).fetchone()
                if old:
                    if old["deleted_at"]:
                        if datetime.fromisoformat(old["deleted_at"]) > datetime.now(
                            UTC
                        ) - timedelta(days=7):
                            raise BVSError(
                                "IDEMPOTENCY_EXPIRED", "The job for this key was deleted"
                            )
                        db.execute("DELETE FROM idempotency WHERE route=? AND key=?", (route, key))
                    else:
                        if old["hash"] != digest:
                            raise BVSError(
                                "IDEMPOTENCY_CONFLICT", "This key was used with a different request"
                            )
                        return self._get(db, old["job_id"])
            if db.execute("SELECT count(*) FROM jobs WHERE state='queued'").fetchone()[0] >= 20:
                raise BVSError("QUEUE_FULL", "Queue is full; wait for a job to finish")
            stamp, job_id = now(), str(uuid4())
            record = dict(
                id=job_id,
                kind=kind,
                state="queued",
                created_at=stamp,
                updated_at=stamp,
                parent_job_id=parent_job_id,
                progress=dict(
                    phase="queued", completed=0, total=None, unit="steps", message="Waiting"
                ),
                engine_id=payload.get("engine_id"),
                model_id=None,
                model_revision=None,
                result=None,
                error=None,
                schema_version=1,
                request_hash=digest,
            )
            record.update(snapshot or {})
            db.execute(
                "INSERT INTO jobs(id,kind,state,request,created_at,updated_at,record) VALUES(?,?,?,?,?,?,?)",
                (job_id, kind, "queued", request, stamp, stamp, canonical(record)),
            )
            if key:
                db.execute(
                    "INSERT INTO idempotency VALUES(?,?,?,?,NULL)", (route, key, digest, job_id)
                )
            return record

    def _get(self, db: sqlite3.Connection, job_id: str) -> dict[str, Any]:
        row = db.execute("SELECT record FROM jobs WHERE id=?", (job_id,)).fetchone()
        if not row:
            raise BVSError("NOT_FOUND", "Job not found")
        return dict(json.loads(row[0]))

    def get(self, job_id: str) -> dict[str, Any]:
        with self.connection() as db:
            return self._get(db, job_id)

    def request(self, job_id: str) -> dict[str, Any]:
        with self.connection() as db:
            self._get(db, job_id)
            return dict(
                json.loads(
                    db.execute("SELECT request FROM jobs WHERE id=?", (job_id,)).fetchone()[0]
                )
            )

    def list(self, *, state: str | None = None, kind: str | None = None) -> list[dict[str, Any]]:
        with self.connection() as db:
            return [
                dict(json.loads(row[0]))
                for row in db.execute(
                    "SELECT record FROM jobs WHERE (? IS NULL OR state=?) AND (? IS NULL OR kind=?) ORDER BY sequence",
                    (state, state, kind, kind),
                )
            ]

    def transition(self, job_id: str, state: str, **updates: Any) -> dict[str, Any]:
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            record = self._get(db, job_id)
            if state not in TRANSITIONS.get(record["state"], set()):
                raise BVSError("INVALID_STATE", "Job state cannot be changed")
            record.update(updates, state=state, updated_at=now())
            db.execute(
                "UPDATE jobs SET state=?,updated_at=?,record=? WHERE id=?",
                (state, record["updated_at"], canonical(record), job_id),
            )
            return record

    def progress(self, job_id: str, progress: dict[str, Any]) -> None:
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            record = self._get(db, job_id)
            if record["state"] != "running":
                return
            record.update(progress=progress, updated_at=now())
            db.execute(
                "UPDATE jobs SET updated_at=?,record=? WHERE id=?",
                (record["updated_at"], canonical(record), job_id),
            )

    def cancel(self, job_id: str) -> dict[str, Any]:
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            record = self._get(db, job_id)
            if record["state"] in TERMINAL or record["state"] == "cancelling":
                return record
            record.update(
                state="cancelled" if record["state"] == "queued" else "cancelling", updated_at=now()
            )
            db.execute(
                "UPDATE jobs SET state=?,updated_at=?,record=? WHERE id=?",
                (record["state"], record["updated_at"], canonical(record), job_id),
            )
            return record

    def recover(self) -> None:
        for record in self.list():
            if record["state"] in {"running", "cancelling"}:
                self.transition(record["id"], "interrupted")
        for directory in (self.directory / "jobs", self.directory / "uploads"):
            if directory.exists():
                for path in directory.rglob("*.part"):
                    path.unlink(missing_ok=True)

    def add_artifact(self, job_id: str, record: dict[str, Any]) -> None:
        with self.connection() as db:
            db.execute(
                "INSERT INTO artifacts VALUES(?,?,?)", (record["id"], job_id, canonical(record))
            )

    def artifact(self, artifact_id: str) -> dict[str, Any]:
        with self.connection() as db:
            row = db.execute("SELECT record FROM artifacts WHERE id=?", (artifact_id,)).fetchone()
            if not row:
                raise BVSError("NOT_FOUND", "Artifact not found")
            return dict(json.loads(row[0]))

    def add_upload(self, record: dict[str, Any]) -> None:
        with self.connection() as db:
            db.execute("INSERT INTO uploads VALUES(?,?)", (record["id"], canonical(record)))

    def upload(self, upload_id: str) -> dict[str, Any]:
        with self.connection() as db:
            row = db.execute("SELECT record FROM uploads WHERE id=?", (upload_id,)).fetchone()
            if not row:
                raise BVSError("NOT_FOUND", "Upload not found")
            return dict(json.loads(row[0]))

    def delete_upload(self, upload_id: str) -> None:
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            for row in db.execute("SELECT kind,state,request FROM jobs"):
                request = json.loads(row["request"])
                depends = (
                    request.get("upload_id") == upload_id
                    or (request.get("reference") or {}).get("upload_id") == upload_id
                )
                if depends and (
                    row["state"] not in TERMINAL
                    or (row["kind"] == "audiobook" and row["state"] != "succeeded")
                ):
                    raise BVSError("INVALID_STATE", "An active or resumable job uses this upload")
            db.execute("DELETE FROM uploads WHERE id=?", (upload_id,))

    def delete(self, job_id: str) -> None:
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            record = self._get(db, job_id)
            if record["state"] not in TERMINAL:
                raise BVSError("INVALID_STATE", "Cancel the job before deletion")
            for row in db.execute("SELECT record FROM jobs"):
                other = json.loads(row[0])
                if other.get("parent_job_id") == job_id:
                    raise BVSError("INVALID_STATE", "Delete dependent resumptions first")
            db.execute("UPDATE idempotency SET deleted_at=? WHERE job_id=?", (now(), job_id))
            db.execute("DELETE FROM artifacts WHERE job_id=?", (job_id,))
            db.execute("DELETE FROM jobs WHERE id=?", (job_id,))
        shutil.rmtree(self.directory / "jobs" / job_id, ignore_errors=True)
