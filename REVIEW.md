# Review: milestone M1 (and the M2 parts that landed)

## What was checked
- Unit and integration suite: 289 tests pass on Python 3.11 and 3.12 in `ci.yml` (ruff, mypy, pytest; no model downloads).
- Browser tests: `e2e.yml` runs the Playwright suite against the dummy engine and passes; it also uploads screenshots and `docs/demo.gif` as an artifact.
- The web UI serves every asset from the package, including the favicon and the bundled Noto Sans Bengali font, so the strict Content-Security-Policy holds with no console errors.
- Real engine adapters import their model libraries lazily inside `load()`; nothing in the default install or test run imports torch, transformers or faster-whisper.
- Repository scanned with gitleaks before each push; no machine paths or credentials in tracked files.

## Fixed during review
- `ci.yml` / `e2e.yml`: the `runner` context is not available in job-level `env`; replaced with fixed temp paths.
- Speech endpoint test: WAV frame count expectation corrected to match the dummy engine's fixed per-character duration.
- Favicon moved from a `data:` URI to a static file so the CSP does not block it.

## Deferred to M3 / needs external evidence
- `models-smoke.yml` (MMS-TTS + faster-whisper round trip) has run green on Python 3.11 and 3.12 and the README carries its CER table. Whisper `small` returns Devanagari script for this Bangla audio, so a larger Whisper model still needs a Bengali-script CER measurement.
- Indic-Parler-TTS, IndicF5 and OmniVoice adapters are written against their documented APIs but are not exercised in CI (too heavy for CPU runners). VoxCPM2-Bangla is registered as unavailable.
- Docker images are built by `docker.yml` on pull requests and tags (green from v0.1.0 on); the CUDA image is a build recipe only and is not exercised.
- Native-speaker review of the normaliser output and an accessibility pass on the UI.
- Model licenses marked "verify on the model card" in `docs/MODEL_LICENSES.md` still need a manual check before any commercial use.
