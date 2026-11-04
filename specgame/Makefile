# Specification Games prototype: environment targets (WP0).
#   make setup      install the pinned toolchain (setup.sh; idempotent)
#   make check      smoke test: compile, SMTChecker proved/counterexample, pyrevm
#   make test       unit tests (tests/, stdlib unittest; some tests run the pinned solc)
#   make lint       speclint on the placeholder artifact and the smoke harness
#   make clean      remove build outputs
#   make distclean  also remove .venv/ and .toolchain/
# Project binaries are always referenced by path, never via the system PATH.

HERE   := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
SOLC   := $(HERE)/.toolchain/bin/solc
Z3     := $(HERE)/.toolchain/bin/z3
PYTHON := $(HERE)/.venv/bin/python

.PHONY: setup check test lint clean distclean

setup:
	bash $(HERE)/setup.sh

TOOLCHAIN_OK = @for f in $(SOLC) $(Z3) $(PYTHON); do \
		test -x $$f || { echo "missing $$f, run 'make setup'"; exit 1; }; \
	done

check:
	$(TOOLCHAIN_OK)
	$(PYTHON) -I -B $(HERE)/smoke/check.py --solc $(SOLC) --z3 $(Z3)

test:
	$(TOOLCHAIN_OK)
	cd $(HERE) && SPECGAME_SOLC=$(SOLC) SPECGAME_Z3=$(Z3) $(PYTHON) -B -m unittest discover -s tests -t . -v

lint:
	$(TOOLCHAIN_OK)
	$(PYTHON) -I -B $(HERE)/tools/speclint.py artifact $(HERE)/subjects/capped_token/CappedToken.sol
	$(PYTHON) -I -B $(HERE)/tools/speclint.py spec $(HERE)/smoke/ProvedTautology.sol --artifact $(HERE)/subjects/capped_token/CappedToken.sol

clean:
	rm -rf $(HERE)/build

distclean: clean
	rm -rf $(HERE)/.venv $(HERE)/.toolchain

# Work-package targets live in mk/<wp>.mk so parallel sessions never edit this file.
-include $(HERE)/mk/*.mk
