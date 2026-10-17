"""Explicit provisioning and verified local model selections."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import re
import shutil
from dataclasses import asdict
from pathlib import Path
from typing import Any

from bvs.config import flag
from bvs.contracts import EngineSpec, Progress, RunContext
from bvs.errors import BVSError

PACKAGES = {
    "mms": "transformers",
    "faster-whisper": "faster-whisper",
    "indic-parler": "parler-tts",
    "indicf5": "f5-tts",
    "omnivoice": "omnivoice",
}
REQUIRED = {
    "mms": {"config.json", "tokenizer_config.json", "vocab.json", "model.safetensors"},
    "faster-whisper": {"config.json", "model.bin", "tokenizer.json", "vocabulary.txt"},
}


def installed(spec: EngineSpec) -> bool:
    if spec.maturity == "test-only":
        return True
    try:
        importlib.metadata.version(PACKAGES.get(spec.id, "__unavailable__"))
    except importlib.metadata.PackageNotFoundError:
        return False
    return True


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(131072), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_suffix(path.suffix + ".part")
    try:
        with part.open("w", encoding="utf-8") as output:
            json.dump(value, output, ensure_ascii=False, sort_keys=True, allow_nan=False)
            output.flush()
            os.fsync(output.fileno())
        os.replace(part, path)
    finally:
        part.unlink(missing_ok=True)


def selection(spec: EngineSpec, cache: Path) -> dict[str, Any]:
    try:
        value = json.loads((cache / "selections" / (spec.id + ".json")).read_text())
    except FileNotFoundError as exc:
        raise BVSError(
            "MODEL_MISSING", f"Run bvs download {spec.id} explicitly on a provisioning host"
        ) from exc
    except (ValueError, OSError) as exc:
        raise BVSError(
            "MODEL_INCOMPLETE", "Model selection is unreadable; provision it again"
        ) from exc
    if (
        not isinstance(value, dict)
        or value.get("model_id") != spec.model_id
        or not re.fullmatch(r"[0-9a-f]{40}", str(value.get("revision", "")))
    ):
        raise BVSError("MODEL_INCOMPLETE", "Model selection identity is invalid")
    if spec.model_revision and value["revision"] != spec.model_revision:
        raise BVSError("MODEL_MISSING", "Selected revision does not match configuration")
    return value


def local_model_path(spec: EngineSpec, cache: Path) -> Path:
    manifest = selection(spec, cache)
    try:
        path: Path = (cache / manifest["path"]).resolve()
        if not path.is_relative_to(cache.resolve()):
            raise ValueError("path")
        files = manifest["files"]
        if not REQUIRED.get(spec.id, set()) <= files.keys() or not files:
            raise ValueError("closure")
        for name, expected in files.items():
            file = (path / name).resolve()
            if (
                not file.is_relative_to(path)
                or file.stat().st_size != expected["bytes"]
                or sha256(file) != expected["sha256"]
            ):
                raise ValueError("checksum")
    except (KeyError, TypeError, AttributeError, ValueError, OSError) as exc:
        raise BVSError(
            "MODEL_INCOMPLETE",
            "Model files are missing or failed integrity checks; provision again",
        ) from exc
    return path


def engine_view(spec: EngineSpec, cache: Path, *, offline: bool) -> dict[str, Any]:
    result = asdict(spec)
    result.pop("factory")
    available = installed(spec)
    state, size, warnings = "ready", None, []
    if spec.maturity == "planned":
        state = "planned"
    elif not available:
        state = "extra_missing"
    elif spec.maturity != "test-only":
        try:
            local_model_path(spec, cache)
            size = sum(f["bytes"] for f in selection(spec, cache)["files"].values())
        except BVSError as exc:
            state = "model_missing" if exc.code == "MODEL_MISSING" else "model_incomplete"
            warnings.append(exc.message)
        if spec.id not in REQUIRED:
            state = "model_incomplete"
            warnings.append("Adapter integration and complete assets await remote validation")
    else:
        size = 0
    result.update(
        installed=available,
        availability=state,
        offline=offline,
        model_bytes_on_disk=size,
        install_hint=f"pip install 'bangla-voice-studio[{spec.pip_extra}]'"
        if spec.pip_extra
        else None,
        readiness_warnings=warnings,
    )
    return result


def download_model(spec: EngineSpec, cache: Path, context: RunContext) -> dict[str, Any]:
    if spec.maturity == "test-only":
        return dict(
            type="download",
            engine_id=spec.id,
            model_id="",
            model_revision="",
            downloaded_bytes=0,
            verified=True,
        )
    if spec.maturity == "planned":
        raise BVSError("ENGINE_UNAVAILABLE", "Not published yet")
    if flag("BVS_OFFLINE") or flag("HF_HUB_OFFLINE") or flag("BVS_TEST_MODE"):
        raise BVSError("OFFLINE", "Explicit model downloads are disabled by offline/test mode")
    if not installed(spec):
        raise BVSError(
            "EXTRA_MISSING",
            f"Install bangla-voice-studio[{spec.pip_extra}] on the provisioning host",
        )
    if spec.id not in REQUIRED:
        raise BVSError("ENGINE_UNAVAILABLE", "Complete offline assets await adapter validation")
    import fcntl

    from huggingface_hub import HfApi, hf_hub_download

    cache.mkdir(parents=True, exist_ok=True)
    with (cache / (spec.id + ".lock")).open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise BVSError("INVALID_STATE", "Another download is using this engine") from exc
        try:
            info = HfApi().model_info(
                spec.model_id, revision=spec.model_revision, files_metadata=True
            )
            revision = str(info.sha)
            names = REQUIRED[spec.id]
            siblings = {s.rfilename: s for s in info.siblings}
            if not names <= siblings.keys():
                raise BVSError(
                    "MODEL_INCOMPLETE", "Required assets are absent from this model revision"
                )
            total = sum(siblings[n].size or 0 for n in names)
            if total <= 0 or shutil.disk_usage(cache).free < total * 2 + 2 * 1024**3:
                raise BVSError(
                    "RESOURCE_LIMIT", "Provisioning needs model storage plus 2 GiB free disk"
                )
            path = cache / "snapshots" / spec.id / revision
            files = {}
            for index, name in enumerate(sorted(names)):
                if context.is_cancelled():
                    raise BVSError("CANCELLED", "Download cancelled")
                downloaded = Path(
                    hf_hub_download(spec.model_id, name, revision=revision, local_dir=str(path))
                )
                files[name] = {"bytes": downloaded.stat().st_size, "sha256": sha256(downloaded)}
                if files[name]["bytes"] != siblings[name].size:
                    raise BVSError(
                        "MODEL_INCOMPLETE", "Downloaded asset size differs from model metadata"
                    )
                context.report(
                    Progress("download", index + 1, len(names), "steps", "Verified model asset")
                )
            manifest = dict(
                model_id=spec.model_id,
                revision=revision,
                path=str(path.relative_to(cache)),
                files=files,
            )
            atomic_json(cache / "selections" / (spec.id + ".json"), manifest)
            return dict(
                type="download",
                engine_id=spec.id,
                model_id=spec.model_id,
                model_revision=revision,
                downloaded_bytes=total,
                verified=True,
            )
        except BVSError:
            raise
        except Exception as exc:
            # Upstream exception text may contain credentials or signed URLs.
            raise BVSError(
                "MODEL_ACCESS_DENIED",
                "Provisioning failed; check model-card access, HF_TOKEN, and network permission",
                retryable=True,
            ) from exc
