PYTHON := .venv/bin/python
RUFF := .venv/bin/ruff
MYPY := .venv/bin/mypy
EXTRAS ?=

.PHONY: install test lint serve

install:
	@command -v uv >/dev/null || { echo 'Install uv first; this target does not download installers.'; exit 1; }
	uv tool install '.$(if $(EXTRAS),[$(EXTRAS)])'

test:
	$(PYTHON) -m pytest -q -x

lint:
	$(RUFF) check src tests scripts
	$(RUFF) format --check src tests scripts
	$(MYPY) src tests scripts

serve:
	$(PYTHON) -m bvs serve
