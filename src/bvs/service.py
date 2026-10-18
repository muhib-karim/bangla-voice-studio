"""Shared validated use cases for CLI and HTTP."""

from __future__ import annotations

import os
import shutil
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, BinaryIO, Self
from uuid import uuid4

from bvs.config import Settings, flag
from bvs.download import engine_view, sha256
from bvs.errors import BVSError
from bvs.jobs.store import TERMINAL, Store
from bvs.media import inspect_wav
from bvs.normalise import normalise
from bvs.registry import get_spec
from bvs.text import chunk_sentence, detect_chapters, split_sentences
from bvs.web.schemas import AudiobookInput, BookPreviewInput, DownloadJobInput, JobKind, JobPayload


def public(record: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in record.items() if k not in {"path", "request_hash", "schema_version"}}


class Service:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.store = Store(settings.data_dir)
        from bvs.jobs.supervisor import Supervisor

        self.supervisor = Supervisor(self.store, settings, self.worker_input)

    def __enter__(self) -> Self:
        self.supervisor.start()
        return self

    def __exit__(self, *args: object) -> None:
        self.supervisor.stop()

    def get_job(self, job_id: str) -> dict[str, Any]:
        return public(self.store.get(job_id))

    def cancel_job(self, job_id: str) -> dict[str, Any]:
        return public(self.store.cancel(job_id))

    def wait(self, job_id: str, *, timeout: float = 7200) -> dict[str, Any]:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            job = self.get_job(job_id)
            if job["state"] in TERMINAL:
                return job
            time.sleep(0.05)
        raise BVSError("TIMEOUT", "Job is still running; inspect its saved job ID", retryable=True)

    def _upload(self, upload_id: str, purpose: str) -> dict[str, Any]:
        record = self.store.upload(upload_id)
        if record["purpose"] != purpose:
            raise BVSError("INVALID_INPUT", f"Upload must have purpose {purpose}")
        return record

    def book_source(self, payload: BookPreviewInput) -> str:
        if payload.text is not None:
            return payload.text
        record = self._upload(str(payload.upload_id), "book")
        return Path(record["path"]).read_text(encoding="utf-8-sig")

    def book_preview(self, payload: BookPreviewInput) -> dict[str, Any]:
        text = self.book_source(payload)
        chapters = detect_chapters(text, format="md")
        rows = []
        for chapter in chapters:
            sentences = split_sentences(chapter.text)
            units = [
                chunk
                for sentence in (chapter.title, *sentences)
                for chunk in chunk_sentence(
                    normalise(sentence) if payload.normalize else sentence,
                    max_chars=payload.max_chars,
                )
            ]
            rows.append(
                dict(
                    index=chapter.index,
                    title=chapter.title,
                    sentence_count=len(sentences),
                    chunk_count=len(units),
                )
            )
        if not rows:
            raise BVSError("INVALID_INPUT", "No narration text remains after parsing")
        return dict(
            chapters=rows,
            total_chars=len(text),
            warnings=["Markdown code and front matter are excluded."]
            if "```" in text or text.startswith("---")
            else [],
        )

    def submit_job(
        self,
        kind: JobKind,
        payload: JobPayload,
        *,
        idempotency_key: str | None = None,
        parent_job_id: str | None = None,
    ) -> dict[str, Any]:
        spec = get_spec(payload.engine_id)
        data = payload.model_dump(mode="json")
        cap = spec.capabilities
        if spec.maturity == "test-only" and not (self.settings.demo or flag("BVS_TEST_MODE")):
            raise BVSError("ENGINE_UNAVAILABLE", "Enable --demo to use test engines")
        if kind == "download":
            if spec.maturity == "planned":
                raise BVSError("ENGINE_UNAVAILABLE", "Not published yet")
            if self.settings.offline and spec.maturity != "test-only":
                raise BVSError("OFFLINE", "Downloads are disabled by offline mode")
        else:
            if spec.kind != ("asr" if kind == "transcription" else "tts"):
                raise BVSError(
                    "UNSUPPORTED_CAPABILITY", "Engine kind does not match this operation"
                )
            if data.get("language") and data["language"] not in cap.languages:
                raise BVSError("UNSUPPORTED_CAPABILITY", "Engine does not support this language")
            if (kind == "clone" or data.get("reference")) and not cap.cloning:
                raise BVSError("UNSUPPORTED_CAPABILITY", "Engine does not support reference voices")
            if cap.reference_required and not data.get("reference"):
                raise BVSError(
                    "UNSUPPORTED_CAPABILITY", "This engine requires a reference clip and transcript"
                )
            if data.get("voice_description") and not cap.voice_description:
                raise BVSError(
                    "UNSUPPORTED_CAPABILITY", "Engine does not support voice descriptions"
                )
            if data.get("word_timestamps") and not cap.word_timestamps:
                raise BVSError("UNSUPPORTED_CAPABILITY", "Engine does not provide word timestamps")
            if ref := data.get("reference"):
                upload = self._upload(ref["upload_id"], "reference")
                if (
                    cap.max_reference_seconds
                    and upload["duration_seconds"] > cap.max_reference_seconds
                ):
                    raise BVSError(
                        "INVALID_MEDIA", "Reference exceeds this engine’s duration limit"
                    )
            if kind == "transcription":
                self._upload(data["upload_id"], "transcription")
            if isinstance(payload, AudiobookInput):
                self.book_preview(payload)
            encoded = any(f != "wav" for f in data.get("formats", []))
            if kind in {"speech", "clone"}:
                sentences = split_sentences(data["text"])
                units = [
                    c
                    for s in sentences
                    for c in chunk_sentence(
                        normalise(s) if data["normalize"] else s,
                        max_chars=cap.max_text_chars or 300,
                    )
                ]
                native = len(units) == 1 and not data.get("reference") and not encoded
            else:
                native = False
            if not native and not shutil.which("ffmpeg"):
                raise BVSError(
                    "EXTRA_MISSING",
                    "Install ffmpeg for multi-unit speech, references, transcription, books, "
                    "and MP3/M4B export",
                )
            view = engine_view(spec, self.settings.model_cache_dir, offline=self.settings.offline)
            if view["availability"] != "ready":
                code = {
                    "extra_missing": "EXTRA_MISSING",
                    "model_missing": "MODEL_MISSING",
                    "model_incomplete": "MODEL_INCOMPLETE",
                    "planned": "ENGINE_UNAVAILABLE",
                }[view["availability"]]
                raise BVSError(
                    code,
                    f"Engine {spec.id} is {view['availability']}; see Engines for install and download steps",
                )
            if flag("BVS_TEST_MODE") and spec.maturity != "test-only":
                raise BVSError("ENGINE_UNAVAILABLE", "Real engines are disabled in test mode")
        model_revision = spec.model_revision
        if kind != "download" and spec.maturity != "test-only":
            from bvs.download import selection

            model_revision = selection(spec, self.settings.model_cache_dir)["revision"]
        job = self.store.create(
            kind,
            data,
            key=idempotency_key,
            parent_job_id=parent_job_id,
            route=f"resume:{parent_job_id}" if parent_job_id else kind,
            snapshot=dict(model_id=spec.model_id, model_revision=model_revision),
        )
        return public(job)

    def download(self, engine_id: str, key: str | None = None) -> dict[str, Any]:
        spec = get_spec(engine_id)
        return self.submit_job(
            "download",
            DownloadJobInput(
                engine_id=engine_id,
                model_id=spec.model_id or "",
                requested_revision=spec.model_revision,
            ),
            idempotency_key=key,
        )

    def resume_audiobook(
        self, job_id: str, *, idempotency_key: str | None = None
    ) -> dict[str, Any]:
        job = self.store.get(job_id)
        if job["kind"] != "audiobook" or job["state"] not in {"failed", "cancelled", "interrupted"}:
            raise BVSError(
                "INVALID_STATE", "Only failed, cancelled, or interrupted books can resume"
            )
        return self.submit_job(
            "audiobook",
            AudiobookInput.model_validate(self.store.request(job_id)),
            idempotency_key=idempotency_key,
            parent_job_id=job_id,
        )

    def artifact(self, artifact_id: str) -> dict[str, Any]:
        record = self.store.artifact(artifact_id)
        path = Path(record["path"]).resolve()
        if (
            not path.is_relative_to((self.settings.data_dir / "jobs").resolve())
            or not path.is_file()
        ):
            raise BVSError("NOT_FOUND", "Artifact is unavailable")
        return record

    def upload(self, stream: BinaryIO, name: str, purpose: str) -> dict[str, Any]:
        limits = {"reference": 20_000_000, "transcription": 250_000_000, "book": 1_000_000}
        if purpose not in limits:
            raise BVSError("INVALID_INPUT", "Unknown upload purpose")
        name = name.replace("\\", "/").rsplit("/", 1)[-1]
        suffix = Path(name).suffix.lower()
        if suffix not in ({".txt", ".md"} if purpose == "book" else {".wav"}):
            raise BVSError(
                "UNSUPPORTED_MEDIA", "Use UTF-8 .txt/.md for books or mono PCM16 .wav for audio"
            )
        upload_id = str(uuid4())
        directory = self.settings.data_dir / "uploads"
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        path = directory / (upload_id + suffix)
        part = path.with_suffix(".part")
        size = 0
        try:
            with part.open("wb") as out:
                while block := stream.read(131072):
                    size += len(block)
                    if size > limits[purpose]:
                        raise BVSError("TOO_LARGE", "Upload exceeds the size limit")
                    out.write(block)
                out.flush()
                os.fsync(out.fileno())
            duration = rate = None
            if purpose == "book":
                try:
                    part.read_text(encoding="utf-8-sig")
                except UnicodeError as exc:
                    raise BVSError("INVALID_MEDIA", "Book must use UTF-8 text") from exc
            else:
                audio = inspect_wav(part)
                rate = audio.sample_rate_hz
                duration = audio.frames / rate
                if purpose == "reference" and not 3 <= duration <= 30:
                    raise BVSError("INVALID_MEDIA", "Reference must be 3–30 seconds")
                if duration > 7200:
                    raise BVSError("TOO_LARGE", "Transcription audio must be at most two hours")
            record = dict(
                id=upload_id,
                name=name,
                purpose=purpose,
                bytes=size,
                sha256=sha256(part),
                media_type="text/plain" if purpose == "book" else "audio/wav",
                duration_seconds=duration,
                sample_rate_hz=rate,
                warnings=[],
                path=str(path),
            )
            os.replace(part, path)
            self.store.add_upload(record)
            return public(record)
        except BaseException:
            path.unlink(missing_ok=True)
            raise
        finally:
            part.unlink(missing_ok=True)

    def delete_upload(self, upload_id: str) -> None:
        record = self.store.upload(upload_id)
        self.store.delete_upload(upload_id)
        Path(record["path"]).unlink(missing_ok=True)

    def worker_input(self, job: dict[str, Any]) -> dict[str, Any]:
        data = self.store.request(job["id"])
        if ref := data.get("reference"):
            ref["path"] = self.store.upload(ref["upload_id"])["path"]
        if data.get("upload_id"):
            data["upload_path"] = self.store.upload(data["upload_id"])["path"]
        return dict(
            job=job,
            payload=data,
            settings={
                **asdict(self.settings),
                "data_dir": str(self.settings.data_dir),
                "model_cache_dir": str(self.settings.model_cache_dir),
                "api_token": None,
            },
        )
