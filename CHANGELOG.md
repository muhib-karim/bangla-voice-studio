# Changelog

## 0.1.2 — 2026-10-18

- Warn when Bangla transcription comes back in Devanagari script. The v0.1.1 model smoke test showed Whisper small does this for MMS-TTS Bangla audio even with `language="bn"`; the transcript now carries a warning instead of passing silently.
- README: results from the v0.1.1 model smoke test.

## 0.1.1 — 2026-10-18

- Pin PyAV below 19 in the `asr` extra: PyAV 19 removed the `metadata_errors` argument that faster-whisper 1.2 passes, which broke transcription on fresh installs (seen on Python 3.12 in the model smoke test).

## 0.1.0 — 2026-10-18

- Bangla normalization with the PLAN examples and local upstream regression fixtures.
- Sentence splitting, bounded text chunks, chapter detection and frame-based SRT/VTT output.
- Deterministic dummy TTS, fake ASR, capability registry and lazy MMS/Whisper loading.
- SQLite jobs, cancellation/restart states, uploads, idempotency and artifact downloads.
- Typer commands and FastAPI routes with a bundled Bangla/English workspace.
- Model-free CI, static Pages site, distribution release, CPU model smoke and browser artifacts.
- CPU/CUDA container recipes and separate model/font license notices.

Real-model support awaits remote validation. Large-engine integrations, chunk-cache reuse,
encoded book exports, measured results and v1 release evidence remain open; see REVIEW.md.
