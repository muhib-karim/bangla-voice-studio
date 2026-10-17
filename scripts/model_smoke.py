"""Explicit Actions-only provisioning, native MMS samples, and Whisper round trips."""

from __future__ import annotations

import argparse
import json
import os
import resource
import shutil
import signal
import time
import unicodedata
from dataclasses import asdict
from pathlib import Path
from typing import Any

from bvs.contracts import ASRRequest, RunContext, RuntimeConfig, SynthesisRequest
from bvs.download import download_model, selection
from bvs.media import read_wav
from bvs.normalise import normalise
from bvs.registry import create_asr, create_tts, get_spec

SENTENCES = (
    "আমি বাংলায় কথা বলি।",
    "আজ আকাশ পরিষ্কার।",
    "আমাদের বাড়ির পাশে একটি নদী আছে।",
    "বই পড়তে আমার ভালো লাগে।",
    "আগামীকাল আবার দেখা হবে।",
)
CONTEXT = RunContext(lambda p: print(p.message, flush=True), lambda: False)


def require_actions() -> None:
    if os.getenv("GITHUB_ACTIONS") != "true" or os.getenv("BVS_MODELS_SMOKE") != "1":
        raise SystemExit("Real model checks run only in the explicit GitHub Actions smoke workflow")
    if os.getenv("BVS_TEST_MODE") == "1":
        raise SystemExit("Real models are forbidden in test mode")


def score_text(text: str) -> str:
    return "".join(
        c.lower()
        for c in unicodedata.normalize("NFC", text)
        if not c.isspace() and not unicodedata.category(c).startswith("P")
    )


def cer(reference: str, heard: str) -> float:
    """Codepoint Levenshtein distance / reference length after NFC and punctuation removal."""
    reference, heard = score_text(reference), score_text(heard)
    if not reference:
        raise ValueError("CER needs a nonempty reference")
    previous = list(range(len(heard) + 1))
    for i, expected in enumerate(reference, 1):
        current = [i]
        for j, actual in enumerate(heard, 1):
            current.append(
                min(current[-1] + 1, previous[j] + 1, previous[j - 1] + (expected != actual))
            )
        previous = current
    return previous[-1] / len(reference)


def budget(path: Path, *, initial: bool = False) -> dict[str, int]:
    free = shutil.disk_usage(path).free
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
    if free < (10 if initial else 2) * 1024**3 or rss > int(5.5 * 1024**3):
        raise RuntimeError("RESOURCE_LIMIT: disk reserve or observed RSS budget exceeded")
    return {"free_disk_bytes": free, "peak_rss_bytes": rss}


def deadline(signum: int, frame: Any) -> None:
    raise TimeoutError("RESOURCE_LIMIT: one fixture exceeded 180 seconds")


def run(phase: str, engine_id: str, cache: Path, output: Path) -> None:
    require_actions()
    output.mkdir(parents=True, exist_ok=True)
    cache.mkdir(parents=True, exist_ok=True)
    before = budget(cache)
    spec = get_spec(engine_id)
    if phase == "provision":
        result = download_model(spec, cache, CONTEXT)
        (output / f"{engine_id}-provision.json").write_text(json.dumps(result, indent=2))
        budget(cache)
        return
    selected = selection(spec, cache)
    runtime = RuntimeConfig(cache, output, spec.model_id, selected["revision"], cpu_threads=2)
    signal.signal(signal.SIGALRM, deadline)
    started = time.monotonic()
    rows: list[dict[str, Any]] = []
    if phase == "synthesize":
        engine = create_tts("mms")
        try:
            engine.load(runtime, CONTEXT)
            for index, sentence in enumerate(SENTENCES, 1):
                signal.alarm(180)
                begin = time.monotonic()
                spoken = normalise(sentence)
                result_tts = engine.synthesize(
                    SynthesisRequest(spoken), output_path=output / f"{index}.wav", context=CONTEXT
                )
                signal.alarm(0)
                samples, rate = read_wav(result_tts.audio.path)
                duration = result_tts.audio.frames / rate
                assert rate == 16000 and 0.1 <= duration <= 60 and samples.any()
                rows.append(
                    dict(
                        id=index,
                        text=spoken,
                        wav=f"{index}.wav",
                        sha256=result_tts.audio.sha256,
                        duration_seconds=duration,
                        synthesis_seconds=time.monotonic() - begin,
                    )
                )
                budget(cache)
        finally:
            signal.alarm(0)
            engine.unload()
        (output / "samples.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2))
    elif phase == "transcribe":
        recognizer = create_asr("faster-whisper")
        samples_manifest = json.loads((output / "samples.json").read_text())
        assert len(samples_manifest) == 5
        try:
            recognizer.load(runtime, CONTEXT)
            for sample in samples_manifest:
                signal.alarm(180)
                begin = time.monotonic()
                transcript = recognizer.transcribe(
                    ASRRequest(output / sample["wav"], language="bn"), context=CONTEXT
                )
                signal.alarm(0)
                assert transcript.text.strip() and transcript.language == "bn"
                last = 0.0
                for segment in transcript.segments:
                    assert (
                        last
                        <= segment.start_seconds
                        <= segment.end_seconds
                        <= transcript.duration_seconds + 1 / 16000
                    )
                    for word in segment.words:
                        assert (
                            segment.start_seconds
                            <= word.start_seconds
                            <= word.end_seconds
                            <= segment.end_seconds
                        )
                    last = segment.end_seconds
                rows.append(
                    {
                        **sample,
                        "transcript": asdict(transcript),
                        "cer": cer(sample["text"], transcript.text),
                        "asr_seconds": time.monotonic() - begin,
                    }
                )
                for warning in transcript.warnings:
                    print(f"WARNING {sample['id']}: {warning}", flush=True)
                budget(cache)
        finally:
            signal.alarm(0)
            recognizer.unload()
        table = ["| Sample | Reference | Whisper small transcript | CER |", "|---|---|---|---|"]
        for row in rows:
            heard = row["transcript"]["text"].replace("|", r"\|").replace("\n", " ")
            table.append(f"| {row['id']} | {row['text']} | {heard} | {row['cer']:.2%} |")
        table.extend(
            [
                "",
                "Five-sentence smoke only; CER measures recoverability through Whisper, not naturalness or voice similarity.",
                "Scoring: NFC, lowercase, remove whitespace and Unicode punctuation, codepoint edit distance / reference length.",
            ]
        )
        warned = sorted({w for row in rows for w in row["transcript"].get("warnings", ())})
        if warned:
            table.extend(["", "Transcript warnings:", *[f"- {w}" for w in warned]])
        (output / "CER.md").write_text("\n".join(table) + "\n")
    else:
        raise ValueError("Unknown smoke phase")
    report = dict(
        engine_id=engine_id,
        model_id=spec.model_id,
        model_revision=selected["revision"],
        code_sha=os.getenv("GITHUB_SHA"),
        license=asdict(spec.license),
        before=before,
        after=budget(cache),
        elapsed_seconds=time.monotonic() - started,
        samples=rows,
    )
    (output / f"{engine_id}-smoke-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2)
    )


if __name__ == "__main__":
    require_actions()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["provision", "synthesize", "transcribe"])
    parser.add_argument("engine", choices=["mms", "faster-whisper"])
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    run(arguments.phase, arguments.engine, arguments.cache, arguments.output)
