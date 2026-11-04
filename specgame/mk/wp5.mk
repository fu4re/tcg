# WP5: bundle assembler + verifier (included by the Makefile via mk/*.mk).
#   make bundle-fixture                 rebuild tests/fixtures/bundle/good (seeded search + tools/bundle.py)
#   make verify-fixture                 tools/verify.py on the fixture bundle (exit 0 HOLDS)
#   make verify-isolated BUNDLE=<dir>   the E1 path: verify <dir> in a container that sees only the bundle

FIXTURE_BUNDLE := $(HERE)/tests/fixtures/bundle

.PHONY: bundle-fixture verify-fixture verify-isolated

bundle-fixture:
	$(TOOLCHAIN_OK)
	$(PYTHON) -I -B $(FIXTURE_BUNDLE)/make_fixture.py

verify-fixture:
	$(TOOLCHAIN_OK)
	$(PYTHON) -I -B $(HERE)/tools/verify.py $(FIXTURE_BUNDLE)/good

verify-isolated:
	@test -n "$(BUNDLE)" || { echo "usage: make verify-isolated BUNDLE=<bundle-dir>"; exit 2; }
	bash $(HERE)/verifier/run_isolated.sh $(BUNDLE)
