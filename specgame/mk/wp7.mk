# WP7: generator loop (gates E3, E5). Included by ../Makefile.
#   make generator-setup   install the hash-pinned anthropic SDK closure into .venv
#   make generator-dry     render every round-1 prompt for the three conditions (no network)
#   make trajectory COND=fM SEED=0   one live trajectory (needs ANTHROPIC_API_KEY or ~/.specgame_env)
COND ?= fM
SEED ?= 0

.PHONY: generator-setup generator-dry trajectory

generator-setup:
	$(TOOLCHAIN_OK)
	$(PYTHON) -m pip install --disable-pip-version-check --no-input --no-cache-dir \
		--require-hashes --only-binary=:all: --no-deps -r $(HERE)/generator/requirements.lock

generator-dry:
	$(TOOLCHAIN_OK)
	@for c in f0 fM fMplus; do $(PYTHON) -I -B $(HERE)/generator/loop.py --condition $$c --seed 0 --dry-run || exit 1; done

trajectory:
	$(TOOLCHAIN_OK)
	$(PYTHON) -I -B $(HERE)/generator/loop.py --condition $(COND) --seed $(SEED)
