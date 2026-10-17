# Skills used

All skill paths below were read from the installed `~/.codex/skills` tree. This was a planning-only task; skill defaults that would create extra design/graph files, install tools, commit, or implement code were superseded by the instruction to produce only `PLAN.md` and `SKILLS_USED.md`.

- [using-superpowers](~/.codex/skills/using-superpowers/SKILL.md) — Read first with its Codex adaptation; applied the requested process skills before design and kept implementation/release execution outside this planning handoff.
- [brainstorming](~/.codex/skills/brainstorming/SKILL.md) — Used the detailed brief as sufficient requirements; compared UI/job/timing alternatives, chose one narration workflow, recorded assumptions/non-goals, and completed a fresh builder check that clarified persisted download identity/revision selection, Docker binding/authentication, and the native-WAV fallback.
- [writing-plans](~/.codex/skills/writing-plans/SKILL.md) — Shaped the plan header, constraints/review focus, exact file/interface ownership, PR-sized milestones, RED/GREEN/refactor/verification steps, and self-review; used the user's requested root `PLAN.md` location.
- [graphify](~/.codex/skills/graphify/SKILL.md) — Applied corpus/availability checks and source-attributed structural mapping; CLI/library were unavailable, so a stdlib AST + direct-source fallback mapped normaliser helpers, callers, tests and TSV dependencies inside PLAN.md; no full Graphify build, clustering, or graph export is claimed.
- [understand](~/.codex/skills/understand/SKILL.md) — Attempted fallback preflight after Graphify runtime absence; no built plugin/core was found in checked install locations, so no Understand pipeline ran and it shaped no additional product decision.
- [api-and-interface-design](~/.codex/skills/api-and-interface-design/SKILL.md) — Shaped exact Engine/ASR contracts, capability validation, versioned typed API schemas, consistent errors, pagination, and transactional idempotency with payload checks and retention.
- [agent-skills-test-driven-development](~/.codex/skills/agent-skills-test-driven-development/SKILL.md) — Put normaliser/contract/job/UI failing tests before each implementation step, preferred real local plumbing driven by dummy/fake engines, and separated deterministic tests from remote real-model evidence; no application tests were claimed as run in this documentation task.
- [ui-ux-pro-max](~/.codex/skills/ui-ux-pro-max/SKILL.md) — Ran the installed local design-system search and one narrower retry plus the focused `error summary validation` UX search; adopted minimal/flat controls, keyboard/error-summary guidance and contrast/touch requirements, while rejecting marketing layouts and CDN/Latin-font suggestions in favour of a local Bangla workspace.
- [ponytail](~/.codex/skills/ponytail/SKILL.md) — Removed Redis/Celery, frontend build tooling, plugin marketplace, waveform editor and speculative abstractions; retained every required v1 workflow, one serial worker, polling, and explicit limits/evidence gates.

Availability note: all eight requested skill documents were available. Graphify's executable/importable package was not available; the additional Understand fallback also lacked a usable runtime in checked locations. No proxy, third-party token handoff, dependency installer, model download, or model inference was used. UI search output was not persisted as a third file.

## Build session (Claude Code)

Installed skill sources: `/home/user/harness/codex_home/skills/<name>/SKILL.md`.

- ponytail — scope — kept one SQLite queue, one worker, plain ES modules, and existing normaliser; decisions in `docs/BUILD_LOG.md`.
- executing-plans — implementation sequence — `docs/BUILD_LOG.md` records results and departures from planning-only/commit steps.
- agent-skills-test-driven-development — behavior — each new test file precedes its module; focused RED/GREEN runs, CI-only browser/model exceptions recorded.
- api-and-interface-design — contracts/routes — `contracts.py`, `web/schemas.py`, consistent errors and idempotency in `jobs/store.py`.
