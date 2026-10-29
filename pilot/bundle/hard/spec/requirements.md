# n: informal specification of MakerDAO GemJoin ETH-A

- **Artefact:** runtime bytecode at `0x2F0b23f53734252Bda2277357e97e1517d6B042A`, keccak256 `0x8661c673677de206fda20eb1883063ea4a827c2ac1c7f232dd30e276d20874fa`, 3462 bytes, Ethereum mainnet, pinned block 26298481.
- **Status:** DRAFT written by the producing agent (WS-H, 2026-10-29) for the author to review. **NOT signed.** The oracle signs `sha256(phi.json) ‖ sha256(requirements.md)` (DECISIONS D4) only after the author has read and, if needed, rewritten this file. Any edit here changes the hash and voids any earlier signature.
- **How to read it:** each `R<n>` states what GemJoin must do, independently of what was proved. Which claims cover which requirement, and what stays uncovered, is in `phi.json` (`claims[].requirements`, `coverage`, `declared_blind_spots`). Most of the value-moving behaviour (R6, R7) is **not proved**. That is the honest result of this bundle, not an omission.
- **Storage layout (deployed):** slot 0 `wards` (mapping address ⇒ uint), 1 `vat`, 2 `ilk`, 3 `gem`, 4 `dec`, 5 `live`.

## Requirements

- **R1** `vat()` succeeds for every caller when sent with zero value, returns the address stored as `vat` (slot 1, low 160 bits), and changes no state.
- **R2** `ilk()` succeeds for every caller when sent with zero value, returns the `bytes32` stored as `ilk` (slot 2), and changes no state.
- **R3** `gem()` succeeds for every caller when sent with zero value, returns the address stored as `gem` (slot 3, low 160 bits), and changes no state.
- **R4** Only a ward (`wards[msg.sender] == 1`) can call `cage()`, `rely(usr)` or `deny(usr)`. For any other caller the call reverts and changes no state.
- **R5** Once the adapter is caged (`live == 0`), `join(usr, wad)` reverts for every caller and every `usr`, `wad`, before making any external call and without changing any state.
- **R6** `join(usr, wad)` with `live == 1` and `wad < 2**255` moves exactly `wad` units of `gem` from `msg.sender` to the adapter (`gem.transferFrom`) and credits `vat.gem[ilk][usr]` by exactly `wad` (`vat.slip(ilk, usr, int(wad))`). It reverts if `wad >= 2**255` or if the transfer fails or returns false.
- **R7** `exit(usr, wad)` with `wad <= 2**255` debits `vat.gem[ilk][msg.sender]` by exactly `wad` (`vat.slip(ilk, msg.sender, -int(wad))`) and transfers exactly `wad` units of `gem` from the adapter to `usr`. It reverts if `wad > 2**255` or if the transfer fails or returns false.
- **R8** No function changes GemJoin's own storage except that `cage()` sets `live` to 0 and `rely`/`deny` set `wards[usr]` to 1/0. `join` and `exit` leave GemJoin's storage unchanged.
- **R9** Every function is non-payable: a call with `msg.value > 0` reverts and changes no state.
