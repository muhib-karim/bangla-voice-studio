"""Validated application paths and local serving policy."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from bvs.errors import BVSError


def flag(name: str) -> bool:
    return os.getenv(name, "").lower() in {"1", "true", "yes", "on"}


def _data() -> Path:
    return Path(
        os.getenv(
            "BVS_DATA_DIR",
            str(Path(os.getenv("XDG_DATA_HOME", str(Path.home() / ".local/share"))) / "bvs"),
        )
    )


def _cache() -> Path:
    return Path(
        os.getenv(
            "BVS_MODEL_CACHE",
            str(Path(os.getenv("XDG_CACHE_HOME", str(Path.home() / ".cache"))) / "bvs/models"),
        )
    )


@dataclass(frozen=True)
class Settings:
    data_dir: Path = field(default_factory=_data)
    model_cache_dir: Path = field(default_factory=_cache)
    demo: bool = False
    api_token: str | None = field(default_factory=lambda: os.getenv("BVS_API_TOKEN"))
    host: str = "127.0.0.1"
    port: int = 8000
    offline: bool = field(default_factory=lambda: flag("BVS_OFFLINE") or flag("HF_HUB_OFFLINE"))

    def __post_init__(self) -> None:
        if not 1 <= self.port <= 65535:
            raise BVSError("INVALID_CONFIG", "Port must be between 1 and 65535")
        if self.host not in {"127.0.0.1", "localhost", "::1"} and not self.api_token:
            raise BVSError(
                "INVALID_CONFIG",
                "A non-loopback host requires BVS_API_TOKEN and a TLS reverse proxy for remote access",
            )
        object.__setattr__(self, "data_dir", self.data_dir.expanduser().resolve())
        object.__setattr__(self, "model_cache_dir", self.model_cache_dir.expanduser().resolve())
