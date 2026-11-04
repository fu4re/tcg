# Protocol v3: subjects. Included by ../Makefile.
#   make portdiff-vat   equivalence of subjects/vat/Vat.sol with the sheaf port (5000 seeded sigmas)
SHEAF_VAT ?= $(HOME)/sheaf/cycle/ground_truth/dss_vat/src/Vat.sol

.PHONY: portdiff-vat

portdiff-vat:
	$(TOOLCHAIN_OK)
	$(PYTHON) -I -B $(HERE)/tools/portdiff.py --subject vat --original $(SHEAF_VAT) --n 5000 \
		--log $(HERE)/subjects/vat/portdiff_log.json
