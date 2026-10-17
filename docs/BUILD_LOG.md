# Build ledger — PLAN.md

Scope: continue existing work; complete M1 and bounded M2 work. The user's build request supersedes the planning-only constraint and commit steps in PLAN.md. No commits, installs, servers, local browser runs, heavy imports, or model downloads.

Rulings:
- Work stays in the supplied checkout; no worktree/commit automation because the operator owns commits.
- Tests run one file at a time until the final suite to bound memory.
- The user pulls segmentation, captions, the audiobook command and packaging forward into this session. WAV audiobook rendering is included; encoded exports remain an explicit M3 prerequisite.
- Remote browser/model checks are authored but cannot be called passing without CI evidence.
- Skill execution bookkeeping is recorded here rather than using commit-dependent scripts.

Baseline: existing normaliser numeric tests 196 passed; reference tests 56 passed. Existing engine/media tests and integration tests are retained. No earlier RED evidence is claimed for inherited files.

Continuation session 4:
- Ruling: `কথা` has three non-whitespace codepoints; PLAN §5 requires 7,200 frames, so the 9,600-frame API assertion was wrong. Observed RED, corrected the assertion, API file GREEN: 6 tests.
- Ruling: the checkout contains no static UI files despite the handoff note. Added a shell/assets test (RED), then implemented the five pages and moved bundled font/OFL under package static assets (GREEN).
- Applied Ruff formatting/import fixes and strict type annotations to inherited code/tests, retaining semantics. Removed constant conditionals from metadata descriptors.
- Added CI, Pages, release, model smoke, E2E and Docker workflows. Local libyaml syntax parser checks all six; no PyYAML installation was needed here.
- Added `scripts/model_smoke.py` after its failing test file; seven model-free metric/guard tests pass. MMS and Whisper run in separate CI jobs, never here.
- Ruling: weekly smoke with five Bangla sentences follows the newer user instruction over PLAN's nightly/three-sentence example. CPU matrices cover both supported Python versions.
- Ruling: keep actual large-engine unavailability and WAV-only/rerender limits visible; do not call descriptor slots real integration support. This session completes the requested continuation files, not v1 release acceptance.
- GitHub DNS is unavailable here. Pages action tags and container digests still require remote pin review; no invented SHA/digest was added.
- Browser screenshots, model CER/resources, dependency resolution, wheel/container builds, human Bangla/a11y review and deployment remain external evidence. No claim that authored workflows have run.
