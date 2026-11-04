# WP1+WP2: subject contract and mutation class M with properness evidence.
#   make mutants                 lint b and every mutant of SUBJECT, then build
#                                subjects/<SUBJECT>/mutants/mutants.json and the properness log
#   make mutants SUBJECT=vat     the same for the Vat subject
# Search parameters (recorded in the log under "params"):
SUBJECT            ?= capped_token
PROPERNESS_SEED    ?= 0
PROPERNESS_BUDGET  ?= 2000
PROPERNESS_MAX_TXS ?= 6
PROPERNESS_LOG     ?= $(HERE)/build/properness_log$(if $(filter-out capped_token,$(SUBJECT)),_$(SUBJECT)).json
SUBJECT_DIR        := $(HERE)/subjects/$(SUBJECT)

.PHONY: mutants

mutants:
	$(TOOLCHAIN_OK)
	@test -d $(SUBJECT_DIR)/mutants || { echo "no $(SUBJECT_DIR)/mutants"; exit 1; }
	@for f in $(wildcard $(SUBJECT_DIR)/*.sol) $(SUBJECT_DIR)/mutants/m*.sol; do \
		$(PYTHON) -I -B $(HERE)/tools/speclint.py artifact $$f --subject $(SUBJECT) || exit 1; done
	SPECGAME_SOLC=$(SOLC) SPECGAME_Z3=$(Z3) $(PYTHON) -I -B $(HERE)/tools/properness.py --subject $(SUBJECT) \
		--mutants $(SUBJECT_DIR)/mutants \
		--seed $(PROPERNESS_SEED) --budget $(PROPERNESS_BUDGET) --max-txs $(PROPERNESS_MAX_TXS) \
		--out $(SUBJECT_DIR)/mutants/mutants.json --log $(PROPERNESS_LOG)
