# Contributing

Read PLAN.md and REVIEW.md before changing behavior. Keep one shared application service for CLI and HTTP, and preserve model-free imports. Write each behavior's focused test before its module or fix, observe the failure, then implement the smallest complete change.

## Local setup and checks

On an ordinary development host, create `.venv` and install `.[dev]`. In a constrained continuation session, use the supplied environment; do not install packages or run model/browser processes.

```sh
.venv/bin/python -m pytest -q -x -p no:cacheprovider tests/unit/test_text.py
.venv/bin/ruff check src tests scripts
.venv/bin/ruff format --check src tests scripts
.venv/bin/mypy src tests scripts
```

While iterating on a constrained host, select one test file per run. Run the full suite once after the final change with `.venv/bin/python -m pytest -q -x`. Ordinary tests block heavy model imports and external sockets. Do not add model packages to the base or dev dependencies, bypass the import guard, or download models to make a unit test pass.

## Remote checks

- `ci.yml`: Python 3.11/3.12, Ruff, strict mypy, pytest, distribution build and fresh-wheel checks; no models.
- `e2e.yml`: Python Playwright/Chromium against a demo server. It captures screenshots, failure traces and a labelled `docs/demo.gif`; do not run this locally in the constrained environment.
- `models-smoke.yml`: manual and weekly CPU MMS → faster-whisper-small, five public Bangla sentences, WAVs, CER and resource reports. Inference has denied egress and a 6 GiB cgroup limit; a missing dependency/model fails rather than using a fake.
- `docker.yml`: CPU build and offline dummy checks on PRs; publish GHCR tags only from `v*` tags after checks.
- `release.yml`: tag/version consistency, reusable checks, sdist/wheel build, GitHub Release attachments. No PyPI publishing in this milestone.

Configure the repository's Pages source as GitHub Actions. Protect `main` and release tags, require CI/E2E reviews, and treat an unrun workflow as pending evidence. This session does not change repository settings, push tags, or publish anything.

Keep Bangla labels with English secondary labels, visible keyboard focus and local font assets. Put user-provided text in `textContent`. Never store private input or tokens in browser storage, log authorization headers, accept arbitrary model IDs from HTTP, or fetch user-provided URLs.

Before a real adapter can be supported: pin and audit its runtime and complete asset closure, verify its model license, test offline loading in a fresh remote process, record resource use, and review actual Bangla output. Changes to the normalizer require fixture/provenance review; do not alter the upstream benchmark's scoring semantics.
