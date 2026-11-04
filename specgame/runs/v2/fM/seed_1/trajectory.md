# Trajectory fM seed 1

Model requested `claude-sonnet-5-5`, returned `claude-sonnet-5-5`; R = 3, k = 2; |W*| = 16 (this trajectory's W_t plus the ladder's W*).

| round | selected | acc | own ms_cert (shown under fM/fMplus) | K_t on W* | event t -> t+1 |
|---|---|---|---|---|---|
| 1 | cand 1 | Accept | 7/8 | 7/8 ['m06_transfer_credits_sender', 'm01_mint_no_owner', 'm03_mint_cap_off_by_one', 'm04_mint_no_supply', 'm05_transfer_no_debit', 'm02_mint_no_cap', 'm07_transfer_no_credit'] | unchanged |
| 2 | cand 1 | Accept | 7/8 | 7/8 ['m06_transfer_credits_sender', 'm01_mint_no_owner', 'm03_mint_cap_off_by_one', 'm04_mint_no_supply', 'm05_transfer_no_debit', 'm02_mint_no_cap', 'm07_transfer_no_credit'] | unchanged |
| 3 | cand 1 | Accept | 7/8 | 7/8 ['m06_transfer_credits_sender', 'm01_mint_no_owner', 'm03_mint_cap_off_by_one', 'm04_mint_no_supply', 'm05_transfer_no_debit', 'm02_mint_no_cap', 'm07_transfer_no_credit'] | - |

Final: bundle_holds
κ = 27 / 27 asserts; vacuity (a) flagged [], unknown []

## Round 1 -> 2: unchanged

```diff
--- round_1/Spec.sol
+++ round_2/Spec.sol
@@ -22,6 +22,16 @@
         require(x > cap - totalSupply);
         mint(a, x);
         assert(false);
+    }
+
+    function check_mint_respects_cap(address a, address b, uint256 x, uint256 y) external {
+        mint(a, x);
+        assert(totalSupply <= cap);
+    }
+
+    function check_transfer_respects_cap(address a, address b, uint256 x, uint256 y) external {
+        transfer(a, x);
+        assert(totalSupply <= cap);
     }
 
     // 3. Minting is exact.
@@ -81,6 +91,13 @@
         assert(false);
     }
 
+    function check_overdraft_keeps_sender_balance(address a, address b, uint256 x, uint256 y) external {
+        uint256 s0 = balanceOf[msg.sender];
+        transfer(a, x);
+        assert(balanceOf[msg.sender] <= s0 || a == msg.sender);
+        assert(x <= s0);
+    }
+
     // 6. Owner and cap are fixed.
     function check_transfer_keeps_owner_and_cap(address a, address b, uint256 x, uint256 y) external {
         address o0 = owner;
```

## Round 2 -> 3: unchanged

```diff
(identical)
```
