"""Isolated model lifecycle and disk-backed rendering."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any
from uuid import uuid4

from bvs.captions import Cue, render_srt, render_vtt
from bvs.contracts import (
    ASRRequest,
    Progress,
    ReferenceAudio,
    RunContext,
    RuntimeConfig,
    SynthesisRequest,
)
from bvs.download import atomic_json, download_model, sha256
from bvs.errors import BVSError
from bvs.media import concatenate_wav, inspect_wav
from bvs.normalise import normalise
from bvs.registry import create_asr, create_tts, get_spec
from bvs.text import chunk_sentence, detect_chapters, split_sentences


def artifact(
    path: Path, media_type: str, *, duration: float | None = None, notes: list[str] | None = None
) -> dict[str, Any]:
    artifact_id = str(uuid4())
    return dict(
        id=artifact_id,
        name=path.name,
        path=str(path),
        media_type=media_type,
        bytes=path.stat().st_size,
        sha256=sha256(path),
        download_url="/api/v1/artifacts/" + artifact_id,
        duration_seconds=duration,
        license_notes=notes or [],
    )


def captions(cues: tuple[Cue, ...], formats: list[str], stem: Path) -> list[dict[str, Any]]:
    result = []
    for fmt in dict.fromkeys(formats):
        path = stem.with_suffix("." + fmt)
        temporary = path.with_suffix("." + fmt + ".part")
        temporary.write_text(
            render_srt(cues) if fmt == "srt" else render_vtt(cues), encoding="utf-8"
        )
        os.replace(temporary, path)
        result.append(artifact(path, "text/vtt" if fmt == "vtt" else "application/x-subrip"))
    return result


def canonical_wav(source: Path, destination: Path) -> Path:
    info = inspect_wav(source)
    if info.sample_rate_hz == 24000:
        return source
    executable = shutil.which("ffmpeg")
    if not executable:
        raise BVSError("EXTRA_MISSING", "Install ffmpeg for canonical 24 kHz audio")
    temporary = destination.with_suffix(".part")
    try:
        subprocess.run(
            [
                executable,
                "-nostdin",
                "-v",
                "error",
                "-y",
                "-i",
                str(source),
                "-ac",
                "1",
                "-ar",
                "24000",
                "-c:a",
                "pcm_s16le",
                "-f",
                "wav",
                str(temporary),
            ],
            check=True,
            capture_output=True,
            timeout=120,
        )
        inspect_wav(temporary)
        os.replace(temporary, destination)
    except (subprocess.SubprocessError, OSError) as exc:
        raise BVSError("EXPORT_FAILED", "Audio conversion failed") from exc
    finally:
        temporary.unlink(missing_ok=True)
    return destination


def run(data: dict[str, Any], workspace: Path, context: RunContext) -> dict[str, Any]:
    job, payload = data["job"], data["payload"]
    spec = get_spec(payload["engine_id"])
    cache = Path(data["settings"]["model_cache_dir"])
    config = RuntimeConfig(cache, workspace, job["model_id"], job["model_revision"])
    if job["kind"] == "download":
        return download_model(spec, cache, context)
    os.environ.update(
        HF_HUB_OFFLINE="1",
        TRANSFORMERS_OFFLINE="1",
        HF_HOME=str(cache / "hf"),
        HF_HUB_CACHE=str(cache / "hf" / "hub"),
    )
    if job["kind"] == "transcription":
        recognizer = create_asr(spec.id)
        try:
            recognizer.load(config, context)
            result = recognizer.transcribe(
                ASRRequest(
                    Path(payload["upload_path"]), payload["language"], payload["word_timestamps"]
                ),
                context=context,
            )
        finally:
            recognizer.unload()
        text_path = workspace / "transcript.txt"
        text_path.write_text(result.text, encoding="utf-8")
        json_path = workspace / "transcript.json"
        atomic_json(json_path, asdict(result))
        cues = tuple(
            Cue(round(s.start_seconds * 1000), round(s.end_seconds * 1000), s.text, "asr-segment")
            for s in result.segments
            if s.end_seconds > s.start_seconds
        )
        files = [
            artifact(text_path, "text/plain"),
            artifact(json_path, "application/json"),
            *captions(cues, payload["captions"], text_path),
        ]
        return dict(
            type="transcript",
            **{k: v for k, v in asdict(result).items() if k not in {"engine_id", "model_revision"}},
            artifacts=files,
        )
    engine = create_tts(spec.id)
    reference = None
    if ref := payload.get("reference"):
        reference = ReferenceAudio(Path(ref["path"]), ref["transcript"], ref["language"])
    is_book = job["kind"] == "audiobook"
    text = payload.get("text") or Path(payload["upload_path"]).read_text(encoding="utf-8-sig")
    chapters = detect_chapters(text, format="md") if is_book else ()
    groups = (
        [(c.title, (c.title, *split_sentences(c.text))) for c in chapters]
        if is_book
        else [("", split_sentences(text))]
    )
    max_chars = min(payload.get("max_chars", 300), spec.capabilities.max_text_chars or 1000)
    plans = [
        (
            title,
            [
                chunk_sentence(normalise(s) if payload["normalize"] else s, max_chars=max_chars)
                for s in sentences
            ],
        )
        for title, sentences in groups
    ]
    total = sum(len(fragments) for _, sentences in plans for fragments in sentences)
    if not total:
        raise BVSError("INVALID_INPUT", "No speech units remain")
    native = total == 1 and not reference and not is_book and not shutil.which("ffmpeg")
    warnings: set[str] = set()
    all_cues: list[Cue] = []
    chapter_results = []
    chapter_paths = []
    clock = completed = 0
    rate = 24000
    try:
        context.report(Progress("loading", 0, None, "steps", "Loading engine"))
        engine.load(config, context)
        for chapter_index, (title, sentences) in enumerate(plans):
            chapter_start = clock
            sentence_paths = []
            for sentence_index, fragments in enumerate(sentences):
                fragment_paths = []
                if sentence_index:
                    clock += 3600
                for fragment_index, spoken in enumerate(fragments):
                    if context.is_cancelled():
                        raise BVSError("CANCELLED", "Rendering cancelled")
                    path = workspace / f"unit-{chapter_index}-{sentence_index}-{fragment_index}.wav"
                    synthesized = engine.synthesize(
                        SynthesisRequest(
                            spoken,
                            payload["language"],
                            reference,
                            payload.get("voice_description"),
                            payload["seed"],
                        ),
                        output_path=path,
                        context=context,
                    )
                    warnings.update(synthesized.warnings)
                    path = (
                        path if native else canonical_wav(path, path.with_name("pcm-" + path.name))
                    )
                    audio = inspect_wav(path)
                    rate = audio.sample_rate_hz
                    all_cues.append(
                        Cue(
                            (clock * 1000 + rate // 2) // rate,
                            ((clock + audio.frames) * 1000 + rate // 2) // rate,
                            spoken,
                            "tts-sentence",
                        )
                    )
                    clock += audio.frames
                    fragment_paths.append(path)
                    completed += 1
                    context.report(
                        Progress(
                            "synthesizing",
                            completed,
                            total,
                            "chunks",
                            f"Chapter {chapter_index + 1}, unit {completed}",
                        )
                    )
                sentence_path = workspace / f"sentence-{chapter_index}-{sentence_index}.wav"
                concatenate_wav(fragment_paths, sentence_path)
                sentence_paths.append(sentence_path)
            chapter_path = workspace / (
                f"chapter-{chapter_index + 1}.wav" if is_book else "speech.wav"
            )
            chapter_audio = concatenate_wav(sentence_paths, chapter_path, pause_frames=3600)
            chapter_paths.append(chapter_path)
            if is_book:
                chapter_results.append(
                    dict(
                        index=chapter_index,
                        title=title,
                        start_ms=chapter_start * 1000 // rate,
                        end_ms=clock * 1000 // rate,
                        artifacts=[
                            artifact(
                                chapter_path, "audio/wav", duration=chapter_audio.frames / rate
                            )
                        ],
                    )
                )
                if chapter_index < len(plans) - 1:
                    clock += payload["chapter_pause_ms"] * 24
    finally:
        engine.unload()
    output = workspace / ("audiobook.wav" if is_book else "speech.wav")
    if is_book:
        final_audio = concatenate_wav(
            chapter_paths, output, pause_frames=payload["chapter_pause_ms"] * 24
        )
    else:
        final_audio = inspect_wav(output)
    cues = tuple(all_cues)
    notes = [f"{spec.license.identifier}; commercial use: {spec.license.commercial_use}"]
    files = [
        artifact(output, "audio/wav", duration=final_audio.frames / rate, notes=notes),
        *captions(cues, payload["captions"], output),
    ]
    if is_book:
        return dict(
            type="audiobook",
            chapters=chapter_results,
            artifacts=files,
            cache_hits=0,
            warnings=sorted(
                warnings
                | {
                    "Chunk-cache resume and encoded exports are deferred to M3; resuming rerenders the book."
                }
            ),
        )
    return dict(
        type="speech", artifacts=files, cues=[asdict(c) for c in cues], warnings=sorted(warnings)
    )


def emit(kind: str, value: Any) -> None:
    print(json.dumps(dict(type=kind, value=value), ensure_ascii=False, allow_nan=False), flush=True)


def main() -> None:
    path = Path(sys.argv[1])
    context = RunContext(
        lambda p: emit("progress", asdict(p)), lambda: (path.parent / "cancel").exists()
    )
    try:
        result = run(json.loads(path.read_text()), path.parent, context)
        emit("result", result)
    except BVSError as exc:
        emit("error", dict(code=exc.code, message=exc.message, details=[], retryable=exc.retryable))
        raise SystemExit(1) from None
    except Exception:
        emit(
            "error",
            dict(
                code="WORKER_FAILED",
                message="Rendering failed; check engine prerequisites and input media",
                details=[],
                retryable=False,
            ),
        )
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
