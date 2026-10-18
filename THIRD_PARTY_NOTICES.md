# Third-party notices

Bangla normalizer vocabulary and regression fixtures derive from `bangla-tts-bench`,
MIT, Copyright (c) 2026 Muhib Karim. See [port provenance](docs/normaliser-port.md)
for the inspected commit, file hashes and intentional behavior changes.

Noto Sans Bengali: Copyright 2022 The Noto Project Authors. SIL Open Font License
1.1, retained at `src/bvs/web/static/fonts/OFL.txt` and shipped with the font.

Model weights and runtime packages have separate terms; see
[MODEL_LICENSES.md](docs/MODEL_LICENSES.md). No model weight is bundled.
ffmpeg and its codecs are distribution packages in container builds; their
upstream copyright and license files remain in the image.

## Container images

- CPU image (`Dockerfile`): built on the official `python:3.11-slim-bookworm`
  image. Debian packages (including ffmpeg) keep their copyright files under
  `/usr/share/doc`. Python packages installed into `/opt/venv` are the base
  install plus the `mms` and `asr` extras with the CPU build of PyTorch; each
  keeps its license in its `*.dist-info` directory. The model-free image built
  by CI measured about 2.2 GB on 2026-10-18; the digest of each published tag is
  written to the Docker workflow's run summary.
- CUDA recipe (`Dockerfile.cuda`): built on `nvidia/cuda` runtime images, which
  carry NVIDIA's CUDA license terms in addition to the packages above. It is
  built and smoke-tested on CPU only by a manual workflow run and is not
  published.
