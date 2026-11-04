# Provenance: subject `vat` (MakerDAO DSS Vat)

| Field | Value |
|---|---|
| Upstream | https://github.com/makerdao/dss, commit `fa4f6630afb0624d04a003e920b0d71a00331d98`, `src/vat.sol` (solc ^0.6.12, AGPL-3.0-or-later) |
| Intermediate | the sheaf repo's equivalence-verified 0.8 port, `cycle/ground_truth/dss_vat/src/Vat.sol`, sheaf commit `c5784c774d9573d91db17d778e31b06968712c7b` |
| Sheaf port sha256 | `6da8363c5a87c3e76cfd49e56c9dda0f596a28a61db7deafd010163966ba6658` |
| Sheaf legacy (0.6.12 original) sha256 | `9016fd94f0f1b014abf184edab86a3f5843042b17e3734407e0f0fabb920f49f` (`legacy/Vat_0_6.sol`) |
| This file | `subjects/vat/Vat.sol`, sha256 `7a86385849359362580286f8d428512ba37653154301bfcbeae16cecf5860748` |

## The one change made here

Every function declared `external` in the sheaf port is declared `public`
here (17 lines; `sed 's/) external /) public /g; s/) external$/) public/'`
reproduces this file byte for byte from the sheaf port). Nothing else is
touched: the pragma stays `^0.8.0` (it admits the pinned solc 0.8.35), and the
comments, including the sheaf port's own, are kept. Why: a spec calls the
subject's functions internally (`contract Spec is Vat`), which `external`
functions do not allow (specs/SPEC_FORMAT.md, section 1).

The sheaf port's own four version-forced changes from 0.6.12 (pragma,
constructor visibility, `unchecked` around the overflow helpers, `||`/`&&`
for the assembly `or`/`and`) and its 4800-operation differential fuzz against
the 0.6.12 bytecode are documented in the sheaf repo's `port_notes.md`; they
are not re-done here.

## Mechanical equivalence of the change (`tools/portdiff.py`)

`python tools/portdiff.py --subject vat --original <sheaf>/cycle/ground_truth/dss_vat/src/Vat.sol --n 5000 --log subjects/vat/portdiff_log.json`

- Both files compiled with the pinned settings (solc 0.8.35, cancun,
  optimizer off, `bytecodeHash: none`) give the **same runtime bytecode**,
  sha256 `cf975b5a6b4f6d67…` (for these value-type signatures, `external` and
  `public` compile identically).
- 5000 seeded σ (typed generator on the Vat profile, seed 0, up to 6
  transactions after the profile's setup): observations (every transaction
  outcome and return, then debt, vice, Line, live, ilks, urns, gem, dai, sin,
  wards, can over the profile's key spaces) **equal on every σ**.
- Coverage of that run (successful calls / calls; generator typed-v2 with
  per-call kinds, the Vat profile's setup with urns for every sender):
  frob 399/846, fork 470/845, grab 430/911, flux 649/899, move 769/872,
  fold 572/814, slip 585/865, file(ilk) 565/850, file(Line) 532/899,
  init 281/912, rely 611/927, cage 314/895, heal 37/885, suck 744/899,
  deny 542/865, hope 834/834, nope 905/905. The equality is exercised on
  successful frob/fork/grab calls, not only implied by the identical bytecode.

The log (`portdiff_log.json`) carries both source and runtime hashes, the
parameters and the distribution id.
