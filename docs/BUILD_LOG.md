# Build ledger — PLAN.md

Scope: continue existing work; complete M1 and bounded M2 work. The user's build request supersedes the planning-only constraint and commit steps in PLAN.md. No commits, installs, servers, local browser runs, heavy imports, or model downloads.

Rulings:
- Work stays in the supplied checkout; no worktree/commit automation because the operator owns commits.
- Tests run one file at a time until the final suite to bound memory.
- The user pulls segmentation, captions, the audiobook command and packaging forward into this session. WAV audiobook rendering is included; encoded exports remain an explicit M3 prerequisite.
- Remote browser/model checks are authored but cannot be called passing without CI evidence.
- Skill execution bookkeeping is recorded here rather than using commit-dependent scripts.

Baseline: existing normaliser numeric tests 196 passed; reference tests 56 passed. Existing engine/media tests and integration tests are retained. No earlier RED evidence is claimed for inherited files.
