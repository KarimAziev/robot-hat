.PHONY: test test-verbose pyright-check ruff-format-check ruff-lint all

PYTHON ?= python
VENV_ACTIVATE ?= .venv/bin/activate
RUN_IN_VENV = if [ -f "$(VENV_ACTIVATE)" ]; then . "$(VENV_ACTIVATE)"; fi;

UNITTEST_FLAGS ?=

ruff-lint:
	$(RUN_IN_VENV) ruff check .

ruff-format-check:
	$(RUN_IN_VENV) ruff format --check .

test:
	$(RUN_IN_VENV) $(PYTHON) -m unittest discover $(UNITTEST_FLAGS)

test-verbose:
	$(MAKE) test UNITTEST_FLAGS=-v

pyright-check:
	$(RUN_IN_VENV) pyright ./tests ./robot_hat

all: test pyright-check ruff-format-check ruff-lint