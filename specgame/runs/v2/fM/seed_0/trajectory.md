# Trajectory fM seed 0

Model requested `claude-sonnet-5-5`, returned `claude-sonnet-5-5`; R = 3, k = 2; |W*| = 15 (this trajectory's W_t plus the ladder's W*).

| round | selected | acc | own ms_cert (shown under fM/fMplus) | K_t on W* | event t -> t+1 |
|---|---|---|---|---|---|
| 1 | cand 1 | Accept | 7/8 | 7/8 ['m06_transfer_credits_sender', 'm01_mint_no_owner', 'm03_mint_cap_off_by_one', 'm04_mint_no_supply', 'm05_transfer_no_debit', 'm02_mint_no_cap', 'm07_transfer_no_credit'] | unchanged |
| 2 | cand 1 | Accept | 7/8 | 7/8 ['m06_transfer_credits_sender', 'm01_mint_no_owner', 'm03_mint_cap_off_by_one', 'm04_mint_no_supply', 'm05_transfer_no_debit', 'm02_mint_no_cap', 'm07_transfer_no_credit'] | unchanged |
| 3 | cand 1 | Accept | 7/8 | 7/8 ['m06_transfer_credits_sender', 'm01_mint_no_owner', 'm03_mint_cap_off_by_one', 'm04_mint_no_supply', 'm05_transfer_no_debit', 'm02_mint_no_cap', 'm07_transfer_no_credit'] | - |

Final: bundle_holds
κ = 29 / 29 asserts; vacuity (a) flagged [], unknown []

## Round 1 -> 2: unchanged

```diff
--- round_1/Spec.sol
+++ round_2/Spec.sol
@@ -18,6 +18,14 @@
         assert(false);
     }
 
+    // 1. Non-owner mint of a small amount (even zero) must also revert.
+    function check_only_owner_mints_small(address a, address b, uint256 x, uint256 y) external {
+        require(msg.sender != owner);
+        require(x <= cap - totalSupply);
+        mint(a, x);
+        assert(false);
+    }
+
     // 2. A mint past the cap must have no effect (it must revert).
     function check_mint_over_cap_reverts(address a, address b, uint256 x, uint256 y) external {
         require(x > cap - totalSupply);
@@ -31,9 +39,28 @@
         assert(totalSupply <= cap);
     }
 
+    // 2. The cap still holds after any transfer.
+    function check_cap_after_transfer(address a, address b, uint256 x, uint256 y) external {
+        transfer(a, x);
+        assert(totalSupply <= cap);
+    }
+
     // 3. A mint is exact: totalSupply and the recipient grow by x, other balances are unchanged.
     function check_mint_exact(address a, address b, uint256 x, uint256 y) external {
         require(a != b);
+        uint256 s0 = totalSupply;
+        uint256 ba0 = balanceOf[a];
+        uint256 bb0 = balanceOf[b];
+        mint(a, x);
+        assert(totalSupply - s0 == x);
+        assert(balanceOf[a] - ba0 == x);
+        assert(balanceOf[b] == bb0);
+    }
+
+    // 3. Mint to the caller itself.
+    function check_mint_to_caller(address a, address b, uint256 x, uint256 y) external {
+        require(a == msg.sender);
+        require(b != a);
         uint256 s0 = totalSupply;
         uint256 ba0 = balanceOf[a];
         uint256 bb0 = balanceOf[b];
@@ -83,9 +110,28 @@
         assert(totalSupply == s0);
     }
 
+    // 4. A transfer where the observed third address is the owner.
+    function check_transfer_other_is_owner(address a, address b, uint256 x, uint256 y) external {
+        require(a != msg.sender);
+        require(owner != a);
+        require(owner != msg.sender);
+        uint256 bo0 = balanceOf[owner];
+        bool ok = transfer(a, x);
+        assert(ok);
+        assert(balanceOf[owner] == bo0);
+    }
+
     // 5. An overdraft must have no effect (it must revert).
     function check_no_overdraft(address a, address b, uint256 x, uint256 y) external {
         require(x > balanceOf[msg.sender]);
+        transfer(a, x);
+        assert(false);
+    }
+
+    // 5. Overdraft by exactly one must also revert.
+    function check_no_overdraft_by_one(address a, address b, uint256 x, uint256 y) external {
+        require(balanceOf[msg.sender] < type(uint256).max);
+        require(x == balanceOf[msg.sender] + 1);
         transfer(a, x);
         assert(false);
     }
```

## Round 2 -> 3: unchanged

```diff
(identical)
```
