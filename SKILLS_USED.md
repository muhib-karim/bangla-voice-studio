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

Skill sources: the installed `<name>/SKILL.md` catalog.

- ponytail — scope — kept one SQLite queue, one worker, plain ES modules, and existing normaliser; decisions in `docs/BUILD_LOG.md`.
- executing-plans — implementation sequence — `docs/BUILD_LOG.md` records results and departures from planning-only/commit steps.
- agent-skills-test-driven-development — behavior — each new test file precedes its module; focused RED/GREEN runs, CI-only browser/model exceptions recorded.
- api-and-interface-design — contracts/routes — `contracts.py`, `web/schemas.py`, consistent errors and idempotency in `jobs/store.py`.
- ponytail — continuation scope — retained the inherited backend, corrected the frame-count assertion in `tests/integration/test_api.py`, and documented unavailable integrations instead of inventing validation.
- agent-skills-test-driven-development — continuation checks — `test_static.py` failed on the missing HTML shell before static implementation; `test_smoke_metrics.py` failed before `scripts/model_smoke.py`, then passed seven scoring/gating cases.
- ui-ux-pro-max — UI — local design-system and error-summary searches; used the form-accessibility result in `static/ui.js`. PLAN.md's Noto Bengali font/tokens superseded the unrelated palette/font suggestions.
- impeccable — UI — context command and craft floor shaped restrained task pages and `site/index.html`; the established PLAN layout supplied the design authority. Mechanical detector ran; no local browser capture is claimed.
- frontend-ui-engineering — UI — `static/styles.css`, `forms.js`, `jobs.js`: semantic controls, focused error summaries, theme tokens, responsive layout, explicit empty/loading/failed states and in-memory drafts.
- playwright-skill — browser evidence — accessible locators, same-origin request routing, screenshot capture and restore/cancel flows in `tests/e2e/test_studio.py`; executed only by `e2e.yml`, per the user's constraint.
- ci-cd-and-automation — automation — all six workflows: small permissions, concurrency groups, separate model-free and model jobs, wheel checks and bounded artifact retention.
- ponytail-review — final review — reviewed changed flows and connected callers; findings and limitations in `REVIEW.md`.
- code-review-and-quality — final review — correctness, security, architecture, performance, typed tests and a mutation check; `REVIEW.md` records evidence.
- ponytail-audit — end audit — traced local inputs through jobs and artifact serving, with one local user/one worker as the load assumption; M3 obligations in `REVIEW.md`.
- ponytail-debt — end audit — scanned shortcut/ponytail comment markers; explicit deferrals also recorded in `REVIEW.md`.

Continuation constraints: no package installation, servers, Playwright, real engine execution, heavy library imports, commits or pushes locally. Browser/model/container runs are authored CI work, not measured outcomes. The supplied plan and continuation steps override skill defaults that would ask for a new design interview, create worktrees, commit, or run browsers here.
