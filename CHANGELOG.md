# Changelog

## Unreleased

- Distribution: wheel checks in the test suite (studio assets, fonts and licence packaged; tests left out; heavy model packages only behind extras; `bvs` console script), a reusable container smoke script used by CI that also checks a clean stop on SIGTERM and prints the image size, and `make wheel`, `make docker`, `make docker-smoke` and `make docker-cuda` targets (PLAN M3.4).

## 0.3.0 — 2026-10-18

- Exports: per-chapter MP3 (128 kbps mono), chaptered AAC-in-M4B (64 kbps mono) with escaped UTF-8 ffmetadata titles and contiguous chapter marks, and speech MP3; encoded files are written atomically and a missing ffmpeg fails before rendering (PLAN M3.3).
- Studio and CLI: audio-format choices on Speak, Clone and Audiobook (MP3 per chapter and a chaptered M4B, on by default for books when ffmpeg is present); `bvs say`/`bvs clone` write MP3 when the output ends in .mp3; book results show how many verified cached chunks were reused.
- Books: chapter-local SRT/VTT that restart at 00:00 for each chapter file, and a `manifest.json` with title, author, engine, chapter times and file hashes (completes PLAN M3.3).

## 0.2.0 — 2026-10-18

- Tests: chapter detection cases for plain-text অধ্যায়/পরিচ্ছেদ headings in both Unicode spellings, sentence lines that only start with a heading word, word headings outranking numbered lines, bare Bengali-digit headings with a title line, Markdown front matter, tilde fences and links, blank input and EPUB refusal (PLAN M3.2).
- Audiobooks: verified chunk cache (PLAN M3.2). Each rendered unit is stored under a key of engine, model revision, spoken text, language, reference audio, voice description and seed, committed atomically with a digest. Re-rendering or resuming a book reuses verified chunks and reports `cache_hits`; a corrupt or truncated chunk is dropped and rendered again, and any change to those inputs misses the cache.
- Tests: integration test that parses exported SRT and VTT independently and checks the cue times are monotonic, identical across formats, and end within the audio (PLAN M3.1).
- Model smoke test: print transcript warnings (such as the Devanagari-script warning) in the job log and list them under the CER table, so they show without opening the JSON report.
- Tests: resuming a cancelled audiobook through the jobs API reuses the chunks already in the verified cache and renders only the rest; a finished book cannot be resumed (PLAN M3.2).

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
