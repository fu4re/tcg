# WP4 + WP6: adversary A, witness sets W, the hand-written ladder (gate E2).
#   make witnesses   adversary on the six ladder specs -> build/witnesses/<phi>.json (+ .log.json)
#   make ladder      Check, adversary, bundle, verify, survivor Checks, events -> bundles/<phi>/,
#                    build/ladder/ladder_report.{md,json}; exit 1 unless every bundle HOLDS and
#                    nesting + Prop. 6.3 hold. Check results are reused when the solc input matches.
#                    phi_full needs ~10 min per Check at 120 000 ms (bundle Check + verify re-run).
#   make ladder LADDER_SPECS_DIR="<dir> ..."  read kappa / vacuity (a) from specreport runs (first match wins)
#   make ladder-report  re-render the report from build/ladder/ladder_report.json (no Check, no verify)
# Protocol v2 values (protocol.json; Check is isolated per check, in a pool of 4):
ADV_SEED          ?= 0
ADV_BUDGET        ?= 2000
ADV_MAX_TXS       ?= 6
ADV_PER_MUTANT    ?= 1
LADDER_TIMEOUT_MS ?= 60000
LADDER_WALL_S     ?= 600
LADDER_SPECS_DIR  ?= $(HERE)/build/specs
LADDER_SPECS      := phi_top phi_owner phi_cap phi_both phi_transfer phi_full

.PHONY: witnesses ladder ladder-report

witnesses:
	$(TOOLCHAIN_OK)
	@for p in $(LADDER_SPECS); do \
		$(PYTHON) -I -B $(HERE)/tools/adversary.py --spec $(HERE)/specs/$$p.sol \
			--seed $(ADV_SEED) --budget $(ADV_BUDGET) --max-txs $(ADV_MAX_TXS) \
			--per-mutant $(ADV_PER_MUTANT) || exit 1; \
	done

ladder:
	$(TOOLCHAIN_OK)
	$(PYTHON) -I -B $(HERE)/tools/ladder.py --timeout-ms $(LADDER_TIMEOUT_MS) --wall-timeout-s $(LADDER_WALL_S) \
		--seed $(ADV_SEED) --budget $(ADV_BUDGET) --max-txs $(ADV_MAX_TXS) --per-mutant $(ADV_PER_MUTANT) \
		--specs-dir $(LADDER_SPECS_DIR)

ladder-report:
	$(TOOLCHAIN_OK)
	$(PYTHON) -I -B $(HERE)/tools/ladder.py --render-only --timeout-ms $(LADDER_TIMEOUT_MS) --specs-dir $(LADDER_SPECS_DIR)

# Vat (protocol v3, step 2): Check(b, phi) per ladder spec with the frozen timeouts; results in build/vat_ladder/check/.
#   make vat-ladder-check     (phi_full first: its 42 isolated checks fill the cache the rungs then hit)
VAT_LADDER := phi_full phi_top phi_auth phi_consent phi_frob phi_frob_guards phi_frob_both phi_fold phi_move_flux phi_grab_heal_suck phi_books

.PHONY: vat-ladder-check vat-ladder

vat-ladder-check:
	$(TOOLCHAIN_OK)
	@mkdir -p $(HERE)/build/vat_ladder/check
	@for p in $(VAT_LADDER); do \
		$(PYTHON) -I -B $(HERE)/tools/check.py $(HERE)/subjects/vat/specs/$$p.sol --subject vat \
			--json $(HERE)/build/vat_ladder/check/$$p.json > $(HERE)/build/vat_ladder/check/$$p.txt; \
		echo "$$p: exit $$? ($$(sed -n 4p $(HERE)/build/vat_ladder/check/$$p.txt))"; \
	done

# Vat ladder end to end (events.LADDERS["vat"]): Check, adversary, bundle -> bundles/vat/<phi>/, verify,
# survivor Checks for phi_full only (Vat survivor Checks over every rung cost hours), events, report
# -> build/vat_ladder/ladder_report.{md,json}. A spec Unknown on b yields a COULD NOT VERIFY bundle
# whose M, W and score steps must still pass. About 1-1.5 h on 4 cores.
vat-ladder:
	$(TOOLCHAIN_OK)
	$(PYTHON) -I -B $(HERE)/tools/ladder.py --subject vat --timeout-ms $(LADDER_TIMEOUT_MS) --wall-timeout-s $(LADDER_WALL_S) \
		--seed $(ADV_SEED) --budget $(ADV_BUDGET) --max-txs $(ADV_MAX_TXS) --per-mutant $(ADV_PER_MUTANT) \
		--survivor-specs phi_full
