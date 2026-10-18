# Bangla Voice Studio

[![CI](https://github.com/muhib-karim/bangla-voice-studio/actions/workflows/ci.yml/badge.svg)](https://github.com/muhib-karim/bangla-voice-studio/actions/workflows/ci.yml)
[![Pages](https://github.com/muhib-karim/bangla-voice-studio/actions/workflows/pages.yml/badge.svg)](https://github.com/muhib-karim/bangla-voice-studio/actions/workflows/pages.yml)
[![Release](https://github.com/muhib-karim/bangla-voice-studio/actions/workflows/release.yml/badge.svg)](https://github.com/muhib-karim/bangla-voice-studio/actions/workflows/release.yml)

Prepare Bangla text, run local speech and transcription jobs, and export WAV audio with SRT/VTT captions. Use the `bvs` CLI or the bundled Bangla/English browser workspace. No hosted inference, CDN assets, frontend build, or automatic model downloads.

**0.1.x pre-release.** The dummy tone and fake transcript workflows are the model-free reference path. MMS-TTS and faster-whisper run for real in the `models-smoke` workflow on GitHub Actions (Python 3.11 and 3.12); measured numbers are in the results section below. Indic-Parler, IndicF5 and OmniVoice are registered but their inference integrations are unavailable. See [REVIEW.md](REVIEW.md) for limits and M3 work. This is not a v1 release claim.

## Demo

The [E2E workflow](https://github.com/muhib-karim/bangla-voice-studio/actions/workflows/e2e.yml) produces screenshots and `docs/demo.gif` as artifacts. **UI demonstration using a test tone.** A durable release GIF and real model samples will be linked after those workflows run; none are claimed here.

Text fallback: enter `আজ ৳৫০ খরচ।`, preview `আজ পঞ্চাশ টাকা খরচ।`, choose the dummy engine, create audio, and download WAV/SRT/VTT. The demo uses generated tones and sample transcripts, not speech recognition or voice cloning.

## Installation

Python 3.11 or 3.12. Linux is the initial target. Install ffmpeg using your system package manager for multi-sentence speech, references, transcription and books. A single reference-free WAV synthesis unit can run without ffmpeg at its native rate.

From a checkout:

```sh
git clone https://github.com/muhib-karim/bangla-voice-studio.git
cd bangla-voice-studio
python -m venv .venv
.venv/bin/python -m pip install .
```

Alternatively, `make install` uses an already installed `uv` to install the CLI from the checkout. `make install EXTRAS=mms,asr` requests those optional packages. It never installs uv or downloads weights.

After a distribution is published, `pipx install bangla-voice-studio` or `uv tool install bangla-voice-studio` will install the base application. Publication is not asserted by this draft.

## Quick start

With the checkout virtual environment activated (`. .venv/bin/activate`):

```sh
bvs normalize '৳৫০'
bvs engines list
bvs say 'আমি বাংলায় বলি।' --engine dummy --output demo.wav --srt --vtt
bvs serve --demo
```

Open <http://127.0.0.1:8000>. Speak previews normalization; Clone accepts a reference WAV and its transcript; Transcribe exports text and captions; Audiobook previews chapters and exports WAV; Engines lists capabilities, availability and terms without loading model libraries. Use `--demo` explicitly for test engines. The English switch and theme choice are saved; text and reference files are not saved in browser storage.

Do not run foreground CLI jobs against a state directory already owned by a server. Stop the server first or choose a separate `BVS_DATA_DIR`. A CLI `--server` client is deferred.

## Real models and offline use

Provision only on a machine with sufficient memory and disk. The development/test environment must not download or run models. On a provisioning host, install CPU Torch from its CPU index before installing the MMS extra:

```sh
python -m pip install 'torch>=2.4,<3' --index-url https://download.pytorch.org/whl/cpu
python -m pip install '.[mms,asr]'
BVS_OFFLINE=0 HF_HUB_OFFLINE=0 bvs download mms
BVS_OFFLINE=0 HF_HUB_OFFLINE=0 bvs download faster-whisper
BVS_OFFLINE=1 HF_HUB_OFFLINE=1 bvs say 'আমি বাংলায় বলি।' --engine mms --output speech.wav
```

Downloads are explicit and serialized. Inference loads local snapshots only. A missing or incomplete model fails with an actionable error. Model snapshots are hashed and their resolved revision is recorded. Default revision pins and complete remote compatibility evidence still need review before a supported real-model release.

`BVS_MODEL_CACHE` sets the model directory; `BVS_DATA_DIR` sets jobs/uploads. Linux defaults follow `XDG_CACHE_HOME` and `XDG_DATA_HOME` (or the usual home directories). `BVS_OFFLINE=1` or `HF_HUB_OFFLINE=1` disables downloads. For Indic-Parler metadata, `BVS_INDIC_PARLER_MODEL_ID` wins over the legacy `INDIC_PARLER_ID`; `BVS_INDIC_PARLER_REVISION` specifies a revision. An override has unknown license/readiness until reviewed and does not enable the currently unavailable integration.

## Engines

| ID / extra | Intended use | Current status | License / commercial use |
|---|---|---|---|
| `dummy` / base | Deterministic 24 kHz test tone; simulated voice controls | Model-free reference implementation | MIT / allowed |
| `fake-asr` / base | Sample transcript with bounded times | Test-only; no recognition | MIT / allowed |
| `mms` / `mms` | Bangla TTS, no cloning | Lazy CPU adapter; remote validation pending | CC-BY-NC-4.0 / **non-commercial** |
| `faster-whisper` / `asr` or `whisper` | Bangla/English/auto, segment and word times | Lazy small-model adapter; remote validation pending | Checkpoint and runtime separately: verify on the model card |
| `indic-parler` / `indic-parler` | Bangla with voice descriptions | Registered; integration unavailable | Unknown / verify on the model card |
| `indicf5` / `indicf5` | Bangla with reference clip + transcript | Registered; integration unavailable | Unknown / verify on the model card |
| `omnivoice` / `omnivoice` | Bangla/English with reference voice | Registered; integration unavailable | Unknown / verify on the model card |
| `voxcpm2-bn` / reserved `voxcpm2` | Future Bangla LoRA | Not published; no load/download action | Base and adapter unknown / verify on the model card |

See [model licenses](docs/MODEL_LICENSES.md). Extras are separate environments when upstream dependencies conflict; there is no `all` extra. Rates, disk/RAM/VRAM and commercial permission must not be inferred from a model's name. Larger engines require a remote GPU audit. EPUB and IndicConformer are not included.

## RESULTS: model smoke test (v0.1.1)

<!-- RESULTS -->

Measured on GitHub Actions (CPU runners), `models-smoke` workflow on the v0.1.1 fix branch, all 4 jobs green: MMS-TTS synthesis and faster-whisper round trip, each on Python 3.11 and 3.12. Five Bangla sentences, synthesized with MMS-TTS (`facebook/mms-tts-ben`), then transcribed by Whisper `small` with `language="bn"`.

| Measure | Python 3.11 | Python 3.12 |
|---|---|---|
| MMS-TTS synthesis, 5 sentences (about 2 s of audio each) | ok | ok, 9.0 s wall time, 0.65 to 0.74 s per sentence, 645 MB peak memory |
| Round-trip CER, raw (Bengali reference vs Whisper output) | 104.3% | 104.3% |
| Round-trip CER, Whisper output mapped from Devanagari to Bengali codepoints | 40.4% | 41.5% |

What the numbers say:

- **Whisper `small` writes Bangla speech in Devanagari script**, even with `language="bn"`. For example, `আমি বাংলায় কথা বলি।` comes back as `आमी बाँनाई कोता बोली`, which is a close phonetic match in the wrong script. The raw CER above about 100% is therefore a script mismatch, not unintelligible audio.
- The mapped CER moves each Devanagari character to the Bengali character at the same offset (the two Unicode blocks are laid out in parallel) and scores again. It is a rough read on how much of the speech Whisper heard, not a formal benchmark: 94 reference characters, 5 sentences, one recognizer.
- Scoring: NFC, lowercase, whitespace and Unicode punctuation removed, codepoint edit distance divided by reference length, summed over the 5 sentences.
- Not measured: naturalness, speaker similarity, and the 50-sentence comparison. For Bangla transcription inside the app, a larger Whisper model is the practical choice; `small` is the smoke-test model because it fits a CPU runner.

## CLI examples

```sh
bvs normalize '২১/০২/২০২৬' --json
bvs say 'নতুন কথা।' --engine dummy --description 'low voice' --output example.wav
bvs clone 'নতুন লেখা।' --engine dummy --reference ref.wav --reference-text 'আগের কথা।' --output clone.wav
bvs transcribe input.wav --engine fake-asr --language bn --srt --vtt --output-dir captions
bvs audiobook book.md --engine dummy --output-dir book-output --formats wav,mp3,m4b --srt
bvs engines list --json
bvs engines download mms
```

`bvs download mms` is the same explicit download command. A reference must be a mono PCM16 WAV, 3–30 seconds and at most 20 MB; transcription accepts that WAV format up to 2 hours/250 MB. Books accept UTF-8 text/Markdown up to 1 MB. Use a voice you have permission to use.

Output files are not overwritten unless `--overwrite` is given. Ctrl-C requests cancellation and reports the job ID. `bvs audiobook --resume JOB_ID` links a new job to the saved request and reuses verified cached chunks, so only the missing parts are rendered. `--formats wav,mp3,m4b` adds an MP3 per chapter and one chaptered M4B (AAC, needs ffmpeg); `bvs say ... --output speech.mp3` writes MP3. Books also get chapter-local SRT/VTT (each starting at 00:00) and a `manifest.json` listing chapters, times and file hashes. Broader media decoding is later M3 work. TTS caption times come from PCM frames, not estimated word alignment.

## Local API and containers

Run `bvs serve` for ordinary engines or `bvs serve --demo` for model-free checks. API paths start with `/api/v1`; `/docs` describes requests and `/health` is a minimal probe. Mutating browser requests use the CSRF cookie/header, Host/Origin checks and same-origin assets. Job submissions support `Idempotency-Key`; reuse the same key and body for transport retries. Requests without a key create new jobs.

The CPU Docker recipe includes MMS/ASR runtime packages, ffmpeg, and no weights. Builds are not validated locally. The operator sets `BVS_API_TOKEN` to a strong private value before starting:

```sh
docker build -t bvs:cpu .
docker run --rm -p 127.0.0.1:8000:8000 -e BVS_API_TOKEN \
  -v bvs-models:/models -v bvs-data:/data bvs:cpu
```

Use username `bvs` and that token in the browser's Basic-auth prompt. API clients use `Authorization: Bearer …`. Broad binding refuses to start without a token; remote access also needs a TLS reverse proxy. Named volumes are writable by UID/GID 10001. For bind mounts, give that user ownership of the mounted directories. SIGTERM stops the supervisor and its worker.

Provisioning on an authorized runtime host:

```sh
docker run --rm -v bvs-models:/models -v bvs-data:/data \
  -e BVS_OFFLINE=0 -e HF_HUB_OFFLINE=0 bvs:cpu download mms
docker run --rm --network none -v bvs-models:/models -v bvs-data:/data \
  bvs:cpu say 'আমি বাংলায় বলি।' --engine mms --output /data/speech.wav
```

Serving a browser needs local networking; use an external firewall to deny egress while keeping loopback access. `Dockerfile.cuda` is an optional build recipe; GPU compatibility, driver/VRAM requirements and publication are deferred until remote validation.

## Development and attribution

See [CONTRIBUTING.md](CONTRIBUTING.md), [the normalizer port](docs/normaliser-port.md), and [REVIEW.md](REVIEW.md). Ordinary tests forbid model imports and external sockets; browsers and real models have separate CI workflows.

Code: [MIT](LICENSE), copyright 2026 Muhib Karim. Models, reference recordings and generated outputs have separate terms. Noto Sans Bengali is bundled under [SIL OFL 1.1](src/bvs/web/static/fonts/OFL.txt). Cite this project using [CITATION.cff](CITATION.cff). The normalizer derives from [bangla-tts-bench](https://github.com/muhib-karim/bangla-tts-bench); see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
