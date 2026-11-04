# WP3: specs, Check, kappa, vacuity. Included by ../Makefile.
# Defaults are the protocol v2 values (protocol.json): Check, kappa and
# vacuity (a) run per check, isolated, in a pool of 4 solc processes.
SPECS_TIMEOUT_MS ?= 60000
SPECS_WALL_S ?= 600

.PHONY: specs havoc

specs:
	$(TOOLCHAIN_OK)
	$(PYTHON) -I -B $(HERE)/tools/specreport.py --timeout-ms $(SPECS_TIMEOUT_MS) --wall-timeout-s $(SPECS_WALL_S)

havoc:
	$(TOOLCHAIN_OK)
	$(PYTHON) -I -B $(HERE)/tools/kappa.py --write-havoc
