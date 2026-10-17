"""Metadata discovery without importing inference libraries."""

from __future__ import annotations

import hashlib
import importlib
import os
import pkgutil
from dataclasses import replace
from pathlib import Path
from typing import Any, cast

from bvs.contracts import (
    ASREngine,
    ASRRequest,
    ASRResult,
    Engine,
    EngineKind,
    EngineSpec,
    LicenseInfo,
    RunContext,
    RuntimeConfig,
    Segment,
    SynthesisRequest,
    SynthesisResult,
    Word,
)
from bvs.errors import BVSError


def list_engines(*, kind: EngineKind | None = None) -> tuple[EngineSpec, ...]:
    specs: dict[str, EngineSpec] = {}
    for name in ("bvs.engines", "bvs.asr"):
        package = importlib.import_module(name)
        for module in pkgutil.iter_modules(package.__path__, name + "."):
            spec = cast(EngineSpec, importlib.import_module(module.name).SPEC)
            if spec.id in specs:
                raise BVSError("ENGINE_UNAVAILABLE", "Duplicate engine ID")
            if spec.id == "indic-parler":
                override = os.getenv("BVS_INDIC_PARLER_MODEL_ID") or os.getenv("INDIC_PARLER_ID")
                if override:
                    spec = replace(
                        spec,
                        model_id=override,
                        model_revision=os.getenv("BVS_INDIC_PARLER_REVISION"),
                        license=LicenseInfo(
                            "LicenseRef-Unknown",
                            None,
                            "unknown",
                            "Override requires manifest review",
                        ),
                        approximate_download_bytes=None,
                    )
            specs[spec.id] = spec
    return tuple(specs[k] for k in sorted(specs) if kind is None or specs[k].kind == kind)


def get_spec(engine_id: str) -> EngineSpec:
    for spec in list_engines():
        if spec.id == engine_id:
            return spec
    raise BVSError("ENGINE_UNAVAILABLE", f"Unknown engine: {engine_id}")


def create_tts(engine_id: str) -> Engine:
    spec = get_spec(engine_id)
    if spec.kind != "tts":
        raise BVSError("UNSUPPORTED_CAPABILITY", "Select a speech synthesis engine")
    return cast(Engine, _make_engine(spec))


def create_asr(engine_id: str) -> ASREngine:
    spec = get_spec(engine_id)
    if spec.kind != "asr":
        raise BVSError("UNSUPPORTED_CAPABILITY", "Select a transcription engine")
    return cast(ASREngine, _make_engine(spec))


class _Adapter:
    def __init__(self, spec: EngineSpec) -> None:
        self.spec = spec
        self.config: RuntimeConfig | None = None
        self.model: Any = None
        self.tokenizer: Any = None
        self.torch: Any = None

    def load(self, config: RuntimeConfig, context: RunContext) -> None:
        if self.config is not None:
            if self.config != config:
                raise BVSError("ENGINE_UNAVAILABLE", "Unload before changing runtime configuration")
            return
        _check_cancel(context)
        if self.spec.maturity == "planned":
            raise BVSError("ENGINE_UNAVAILABLE", "Not published yet")
        if self.spec.maturity != "test-only":
            from bvs.download import local_model_path

            path = local_model_path(self.spec, config.model_cache_dir)
            try:
                if self.spec.id == "mms":
                    self.torch = importlib.import_module("torch")
                    transformers = importlib.import_module("transformers")
                    self.torch.set_num_threads(config.cpu_threads)
                    self.tokenizer = transformers.AutoTokenizer.from_pretrained(
                        str(path), local_files_only=True
                    )
                    self.model = (
                        transformers.VitsModel.from_pretrained(str(path), local_files_only=True)
                        .to(config.device)
                        .eval()
                    )
                    if self.model.config.sampling_rate != self.spec.capabilities.sample_rate_hz:
                        raise BVSError(
                            "MODEL_INCOMPLETE", "Model sample rate differs from descriptor"
                        )
                elif self.spec.id == "faster-whisper":
                    runtime = importlib.import_module("faster_whisper")
                    self.model = runtime.WhisperModel(
                        str(path),
                        device=config.device,
                        compute_type="int8" if config.device == "cpu" else "float16",
                        cpu_threads=config.cpu_threads,
                        local_files_only=True,
                    )
                else:
                    raise BVSError(
                        "ENGINE_UNAVAILABLE",
                        "Upstream integration and full offline asset closure await remote validation",
                    )
            except ImportError as exc:
                raise BVSError(
                    "EXTRA_MISSING", f"Install bangla-voice-studio[{self.spec.pip_extra}]"
                ) from exc
        self.config = config

    def synthesize(
        self, request: SynthesisRequest, *, output_path: Path, context: RunContext
    ) -> SynthesisResult:
        import numpy as np

        from bvs.media import write_wav

        self._ready(context)
        cap = self.spec.capabilities
        if not request.text.strip():
            raise BVSError("INVALID_TEXT", "Prepared text is empty")
        if (
            request.language not in cap.languages
            or (request.reference and not cap.cloning)
            or (request.voice_description and not cap.voice_description)
            or (cap.reference_required and not request.reference)
        ):
            raise BVSError(
                "UNSUPPORTED_CAPABILITY",
                "Engine does not support the requested language or voice controls",
            )
        if cap.max_text_chars and len(request.text) > cap.max_text_chars:
            raise BVSError("TEXT_TOO_LONG", f"Use at most {cap.max_text_chars} characters per unit")
        if self.spec.id == "dummy":
            voice = request.voice_description or ""
            if request.reference:
                voice += (
                    hashlib.sha256(request.reference.wav_path.read_bytes()).hexdigest()
                    + request.reference.transcript
                )
            output: list[int] = []
            for char in request.text:
                if char.isspace():
                    continue
                digest = hashlib.sha256(f"{char}:{request.seed}:{voice}".encode()).digest()
                step = 200 + int.from_bytes(digest[:2], "big") % 1800
                for frame in range(2400):
                    phase = (frame * step) % 65536
                    output.append((phase if phase < 32768 else 65535 - phase) // 2 - 8192)
            audio = write_wav(output_path, np.asarray(output, dtype=np.int16), 24000)
            return SynthesisResult(audio, self.spec.id, None, ("Demo tone — not speech.",))
        self.torch.manual_seed(request.seed)
        inputs = self.tokenizer(request.text, return_tensors="pt").to(
            self.config.device if self.config else "cpu"
        )
        with self.torch.no_grad():
            samples = self.model(**inputs).waveform[0].detach().cpu().numpy()
        audio = write_wav(output_path, samples, self.model.config.sampling_rate)
        return SynthesisResult(audio, self.spec.id, self.spec.model_revision)

    def transcribe(self, request: ASRRequest, *, context: RunContext) -> ASRResult:
        import numpy as np

        from bvs.media import read_wav

        self._ready(context)
        data, rate = read_wav(request.audio_path)
        duration = len(data) / rate
        language = request.language or "bn"
        if not len(data) or not np.any(data):
            return ASRResult(
                "",
                language,
                duration,
                (),
                False,
                self.spec.id,
                self.spec.model_revision,
                ("No speech detected in empty or silent audio.",),
            )
        if self.spec.id == "fake-asr":
            text = "নমুনা প্রতিলিপি" if language == "bn" else "Sample transcript"
            words: tuple[Word, ...] = (
                (Word(text, 0.0, duration),) if request.word_timestamps else ()
            )
            segments: tuple[Segment, ...] = (Segment(text, 0.0, duration, words),)
            return ASRResult(
                text,
                language,
                duration,
                segments,
                request.word_timestamps,
                self.spec.id,
                None,
                ("Simulated fixture transcript — not recognition.",),
            )
        raw_segments, info = self.model.transcribe(
            str(request.audio_path),
            language=request.language,
            word_timestamps=request.word_timestamps,
        )
        segments_list = []
        for raw in raw_segments:
            _check_cancel(context)
            words = tuple(Word(w.word, w.start, w.end, w.probability) for w in (raw.words or ()))
            segments_list.append(Segment(raw.text, raw.start, raw.end, words))
        segments = tuple(segments_list)
        from bvs.script_check import bangla_script_warnings

        text = "".join(s.text for s in segments).strip()
        return ASRResult(
            text,
            info.language,
            duration,
            segments,
            request.word_timestamps,
            self.spec.id,
            self.spec.model_revision,
            bangla_script_warnings(text, request.language),
        )

    def _ready(self, context: RunContext) -> None:
        _check_cancel(context)
        if self.config is None:
            raise BVSError("ENGINE_UNAVAILABLE", "Load engine before use")

    def unload(self) -> None:
        self.model = self.tokenizer = self.torch = None
        self.config = None


def _check_cancel(context: RunContext) -> None:
    if context.is_cancelled():
        raise BVSError("CANCELLED", "Operation cancelled")


def _make_engine(spec: EngineSpec) -> _Adapter:
    return _Adapter(spec)
