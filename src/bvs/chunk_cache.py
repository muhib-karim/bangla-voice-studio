"""Content-addressed cache of rendered audiobook chunks.

A chunk is keyed by everything that changes its audio: engine, model and
revision, the spoken text after normalisation, language, reference audio,
voice description and seed. Entries are committed atomically with a sidecar
digest, so a truncated or corrupt file is never served: it is dropped and the
chunk is rendered again.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path
from typing import Any

from bvs.download import atomic_json, sha256
from bvs.errors import BVSError
from bvs.media import inspect_wav

CACHE_VERSION = 1
_HEX = frozenset("0123456789abcdef")


def chunk_key(**parts: Any) -> str:
    """Stable hex key for one synthesis unit."""
    blob = json.dumps(
        {"cache_version": CACHE_VERSION, **parts},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


class ChunkCache:
    """Verified chunk store rooted outside any single job workspace."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.hits = 0

    def _paths(self, key: str) -> tuple[Path, Path]:
        if len(key) != 64 or not set(key) <= _HEX:
            raise BVSError("INVALID_INPUT", "Malformed chunk cache key")
        folder = self.root / key[:2]
        return folder / f"{key}.wav", folder / f"{key}.json"

    def fetch(self, key: str, destination: Path) -> bool:
        """Copy a verified entry to ``destination``; drop it and miss on any mismatch."""
        audio, meta = self._paths(key)
        if not audio.exists() and not meta.exists():
            return False
        try:
            recorded = json.loads(meta.read_text(encoding="utf-8"))
            if recorded.get("sha256") != sha256(audio):
                raise ValueError("digest mismatch")
            inspect_wav(audio)
        except (OSError, ValueError, BVSError):
            for stale in (audio, meta):
                stale.unlink(missing_ok=True)
            return False
        part = destination.with_name(destination.name + ".part")
        shutil.copyfile(audio, part)
        os.replace(part, destination)
        self.hits += 1
        return True

    def store(self, key: str, source: Path) -> None:
        """Commit ``source`` under ``key``: audio first, digest last."""
        audio, meta = self._paths(key)
        audio.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        part = audio.with_name(audio.name + ".part")
        shutil.copyfile(source, part)
        with part.open("rb") as handle:
            os.fsync(handle.fileno())
        os.replace(part, audio)
        atomic_json(meta, {"cache_version": CACHE_VERSION, "sha256": sha256(audio)})
