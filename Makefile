.PHONY: test pyright-check ruff-format-check ruff-lint all

PYTHON ?= python
VENV_ACTIVATE ?= .venv/bin/activate

ruff-lint:
	if [ -f "$(VENV_ACTIVATE)" ]; then . "$(VENV_ACTIVATE)"; fi; ruff check .

ruff-format-check:
	if [ -f "$(VENV_ACTIVATE)" ]; then . "$(VENV_ACTIVATE)"; fi; ruff format --check .

test:
	if [ -f "$(VENV_ACTIVATE)" ]; then . "$(VENV_ACTIVATE)"; fi; $(PYTHON) -m unittest discover

pyright-check:
	if [ -f "$(VENV_ACTIVATE)" ]; then . "$(VENV_ACTIVATE)"; fi; pyright ./tests ./robot_hat

all: test pyright-check ruff-format-check ruff-lint