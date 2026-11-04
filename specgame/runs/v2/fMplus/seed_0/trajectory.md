# Trajectory fMplus seed 0

Model requested `claude-sonnet-5-5`, returned `claude-sonnet-5-5`; R = 3, k = 2; |W*| = 14 (this trajectory's W_t plus the ladder's W*).

| round | selected | acc | own ms_cert (shown under fM/fMplus) | K_t on W* | event t -> t+1 |
|---|---|---|---|---|---|
| 1 | cand 1 | Accept | 7/8 | 7/8 ['m06_transfer_credits_sender', 'm01_mint_no_owner', 'm03_mint_cap_off_by_one', 'm04_mint_no_supply', 'm05_transfer_no_debit', 'm02_mint_no_cap', 'm07_transfer_no_credit'] | unchanged |
| 2 | cand 1 | Accept | 7/8 | 7/8 ['m06_transfer_credits_sender', 'm01_mint_no_owner', 'm03_mint_cap_off_by_one', 'm04_mint_no_supply', 'm05_transfer_no_debit', 'm02_mint_no_cap', 'm07_transfer_no_credit'] | unchanged |
| 3 | cand 1 | Accept | 7/8 | 7/8 ['m06_transfer_credits_sender', 'm01_mint_no_owner', 'm03_mint_cap_off_by_one', 'm04_mint_no_supply', 'm05_transfer_no_debit', 'm02_mint_no_cap', 'm07_transfer_no_credit'] | - |

Final: bundle_holds
κ = 25 / 25 asserts; vacuity (a) flagged [], unknown []

## Round 1 -> 2: unchanged

```diff
--- round_1/Spec.sol
+++ round_2/Spec.sol
@@ -88,7 +88,7 @@
         assert(false);
     }
 
-    // 6. Owner and cap fixed under mint and transfer.
+    // 6. Owner and cap fixed under transfer.
     function check_owner_cap_fixed_transfer(address a, address b, uint256 x, uint256 y) external {
         address o0 = owner;
         uint256 c0 = cap;
```

## Round 2 -> 3: unchanged

```diff
(identical)
```
