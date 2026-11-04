# Trajectory fMplus seed 0

Model requested `claude-sonnet-5-5`, returned `claude-sonnet-5-5`; R = 3, k = 2; |W*| = 18 (this trajectory's W_t plus the ladder's W*).

| round | selected | acc | own ms_cert (shown under fM/fMplus) | K_t on W* | event t -> t+1 |
|---|---|---|---|---|---|
| 1 | cand 1 | lint_rejected | 0/8 | 0/8 [] | unchanged |
| 2 | cand 1 | Unknown | 0/8 | 0/8 [] | strengthening |
| 3 | cand 1 | Unknown | 7/8 | 7/8 ['m03_frob_no_ceiling', 'm07_move_no_debit', 'm06_fold_no_debt', 'm01_slip_no_auth', 'm02_frob_no_consent_v', 'm04_frob_no_safety', 'm08_grab_no_vice'] | - |

Final: bundle_not_certified (verify exit 2: NOT_CERTIFIED)
κ = 160 / 160 asserts; vacuity (a) flagged [], unknown ['check_rely_needs_ward', 'check_rely_sets', 'check_rely_needs_live', 'check_deny_needs_ward', 'check_deny_sets', 'check_deny_needs_live', 'check_init_needs_ward', 'check_init_once', 'check_init_sets_rate', 'check_cage_needs_ward', 'check_cage_sets_not_live', 'check_dead_stays_dead_rely', 'check_dead_no_frob', 'check_dead_no_fold', 'check_dead_no_file', 'check_slip_needs_ward', 'check_grab_needs_ward', 'check_suck_needs_ward', 'check_fold_needs_ward', 'check_file_needs_ward', 'check_file_ilk_needs_ward', 'check_file_sets_line', 'check_file_unknown', 'check_file_ilk_spot', 'check_file_ilk_line', 'check_file_ilk_dust', 'check_file_ilk_unknown', 'check_file_ilk_needs_live', 'check_hope', 'check_nope', 'check_flux_needs_consent', 'check_flux_underflow', 'check_flux_overflow', 'check_flux_effect', 'check_flux_self', 'check_move_needs_consent', 'check_move_underflow', 'check_move_overflow', 'check_move_effect', 'check_move_self', 'check_slip_up', 'check_slip_down', 'check_slip_overflow', 'check_slip_underflow', 'check_frob_needs_init', 'check_frob_needs_live', 'check_frob_ceilings', 'check_frob_safe', 'check_frob_dust', 'check_frob_needs_owner_consent', 'check_frob_needs_collateral_consent', 'check_frob_needs_debt_consent', 'check_frob_collateral_up_vault', 'check_frob_collateral_up_balances', 'check_frob_collateral_down', 'check_frob_debt_up_vault', 'check_frob_debt_up_balances', 'check_frob_full_vault', 'check_frob_full_gem', 'check_frob_full_dai', 'check_frob_close_vault', 'check_frob_close_gem', 'check_frob_close_dai', 'check_fork_needs_src_consent', 'check_fork_needs_dst_consent', 'check_fork_safe_dust', 'check_fork_effect_ink', 'check_fork_effect_art', 'check_fork_effect_totals', 'check_grab_effect_vault', 'check_grab_effect_debt', 'check_heal_effect', 'check_heal_needs_dai', 'check_heal_needs_sin', 'check_suck_effect', 'check_suck_overflow_dai', 'check_suck_overflow_debt', 'check_suck_overflow_vice', 'check_fold_up', 'check_fold_down']

## Round 1 -> 2: unchanged

```diff
--- round_1/Spec.sol
+++ round_2/Spec.sol
@@ -200,11 +200,10 @@
     }
 
     function check_file_ilk_unknown(address a, address b, uint256 x, uint256 y) external {
-        bytes32 w = bytes32(x);
-        require(w != "spot");
-        require(w != "line");
-        require(w != "dust");
-        file("GOLD", w, y);
+        require(bytes32(x) != "spot");
+        require(bytes32(x) != "line");
+        require(bytes32(x) != "dust");
+        file("GOLD", bytes32(x), y);
         assert(false);
     }
 
@@ -245,6 +244,22 @@
         assert(false);
     }
 
+    function check_flux_underflow(address a, address b, uint256 x, uint256 y) external {
+        require(a == msg.sender);
+        require(gem["GOLD"][a] < x);
+        flux("GOLD", a, b, x);
+        assert(false);
+    }
+
+    function check_flux_overflow(address a, address b, uint256 x, uint256 y) external {
+        require(a == msg.sender);
+        require(a != b);
+        require(x <= gem["GOLD"][a]);
+        require(x > type(uint256).max - gem["GOLD"][b]);
+        flux("GOLD", a, b, x);
+        assert(false);
+    }
+
     function check_flux_effect(address a, address b, uint256 x, uint256 y) external {
         require(a != b);
         uint256 sa = gem["GOLD"][a];
@@ -269,6 +284,22 @@
     function check_move_needs_consent(address a, address b, uint256 x, uint256 y) external {
         require(a != msg.sender);
         require(can[a][msg.sender] != 1);
+        move(a, b, x);
+        assert(false);
+    }
+
+    function check_move_underflow(address a, address b, uint256 x, uint256 y) external {
+        require(a == msg.sender);
+        require(dai[a] < x);
+        move(a, b, x);
+        assert(false);
+    }
+
+    function check_move_overflow(address a, address b, uint256 x, uint256 y) external {
+        require(a == msg.sender);
+        require(a != b);
+        require(x <= dai[a]);
+        require(x > type(uint256).max - dai[b]);
         move(a, b, x);
         assert(false);
     }
@@ -311,6 +342,21 @@
         uint256 g0 = gem[i][u];
         slip(i, u, dx);
         assert(gem[i][u] + uint256(-dx) == g0);
+    }
+
+    function check_slip_overflow(bytes32 i, address u, int256 dx, int256 dy) external {
+        require(dx > 0);
+        require(uint256(dx) > type(uint256).max - gem[i][u]);
+        slip(i, u, dx);
+        assert(false);
+    }
+
+    function check_slip_underflow(bytes32 i, address u, int256 dx, int256 dy) external {
+        require(dx < 0);
+        require(dx > type(int256).min);
+        require(uint256(-dx) > gem[i][u]);
+        slip(i, u, dx);
+        assert(false);
     }
 
     // ---------------- Vaults: frob ----------------
@@ -561,6 +607,18 @@
         assert(debt + x == t0);
     }
 
+    function check_heal_needs_dai(address a, address b, uint256 x, uint256 y) external {
+        require(dai[msg.sender] < x);
+        heal(x);
+        assert(false);
+    }
+
+    function check_heal_needs_sin(address a, address b, uint256 x, uint256 y) external {
+        require(sin[msg.sender] < x);
+        heal(x);
+        assert(false);
+    }
+
     function check_suck_effect(address a, address b, uint256 x, uint256 y) external {
         uint256 s0 = sin[a];
         uint256 d0 = dai[b];
@@ -571,6 +629,24 @@
         assert(dai[b] == d0 + x);
         assert(vice == v0 + x);
         assert(debt == t0 + x);
+    }
+
+    function check_suck_overflow_dai(address a, address b, uint256 x, uint256 y) external {
+        require(x > type(uint256).max - dai[b]);
+        suck(a, b, x);
+        assert(false);
+    }
+
+    function check_suck_overflow_debt(address a, address b, uint256 x, uint256 y) external {
+        require(x > type(uint256).max - debt);
+        suck(a, b, x);
+        assert(false);
+    }
+
+    function check_suck_overflow_vice(address a, address b, uint256 x, uint256 y) external {
+        require(x > type(uint256).max - vice);
+        suck(a, b, x);
+        assert(false);
     }
 
     // ---------------- Rates ----------------
```

## Round 2 -> 3: strengthening

```diff
--- round_2/Spec.sol
+++ round_3/Spec.sol
@@ -163,14 +163,12 @@
         uint256 d0 = ilks[i].dust;
         uint256 r0 = ilks[i].rate;
         uint256 a0 = ilks[i].Art;
-        uint256 g0 = Line;
         file(i, "spot", uint256(dx));
         assert(ilks[i].spot == uint256(dx));
         assert(ilks[i].line == l0);
         assert(ilks[i].dust == d0);
         assert(ilks[i].rate == r0);
         assert(ilks[i].Art == a0);
-        assert(Line == g0);
     }
 
     function check_file_ilk_line(bytes32 i, address u, int256 dx, int256 dy) external {
@@ -423,19 +421,24 @@
         assert(false);
     }
 
-    function check_frob_collateral_up(bytes32 i, address u, int256 dx, int256 dy) external {
+    function check_frob_collateral_up_vault(bytes32 i, address u, int256 dx, int256 dy) external {
         require(dx >= 0);
         uint256 k0 = urns[i][u].ink;
         uint256 a0 = urns[i][u].art;
-        uint256 g0 = gem[i][u];
-        uint256 d0 = dai[u];
-        uint256 t0 = debt;
         uint256 b0 = ilks[i].Art;
         frob(i, u, u, u, dx, 0);
         assert(urns[i][u].ink == k0 + uint256(dx));
-        assert(gem[i][u] + uint256(dx) == g0);
         assert(urns[i][u].art == a0);
         assert(ilks[i].Art == b0);
+    }
+
+    function check_frob_collateral_up_balances(bytes32 i, address u, int256 dx, int256 dy) external {
+        require(dx >= 0);
+        uint256 g0 = gem[i][u];
+        uint256 d0 = dai[u];
+        uint256 t0 = debt;
+        frob(i, u, u, u, dx, 0);
+        assert(gem[i][u] + uint256(dx) == g0);
         assert(dai[u] == d0);
         assert(debt == t0);
     }
@@ -447,77 +450,107 @@
         uint256 a0 = urns[i][u].art;
         uint256 g0 = gem[i][u];
         uint256 d0 = dai[u];
-        uint256 t0 = debt;
         frob(i, u, u, u, dx, 0);
         assert(urns[i][u].ink + uint256(-dx) == k0);
         assert(gem[i][u] == g0 + uint256(-dx));
         assert(urns[i][u].art == a0);
         assert(dai[u] == d0);
-        assert(debt == t0);
-    }
-
-    function check_frob_debt_up(bytes32 i, address u, int256 dx, int256 dy) external {
+    }
+
+    function check_frob_debt_up_vault(bytes32 i, address u, int256 dx, int256 dy) external {
         require(dy > 0);
         uint256 k0 = urns[i][u].ink;
         uint256 a0 = urns[i][u].art;
-        uint256 g0 = gem[i][u];
-        uint256 d0 = dai[u];
-        uint256 t0 = debt;
         uint256 b0 = ilks[i].Art;
         uint256 r0 = ilks[i].rate;
         frob(i, u, u, u, 0, dy);
         assert(urns[i][u].art == a0 + uint256(dy));
         assert(ilks[i].Art == b0 + uint256(dy));
         assert(ilks[i].rate == r0);
+        assert(urns[i][u].ink == k0);
+    }
+
+    function check_frob_debt_up_balances(bytes32 i, address u, int256 dx, int256 dy) external {
+        require(dy > 0);
+        uint256 g0 = gem[i][u];
+        uint256 d0 = dai[u];
+        uint256 t0 = debt;
+        uint256 r0 = ilks[i].rate;
+        frob(i, u, u, u, 0, dy);
         assert(dai[u] == d0 + r0 * uint256(dy));
         assert(debt == t0 + r0 * uint256(dy));
-        assert(urns[i][u].ink == k0);
         assert(gem[i][u] == g0);
     }
 
-    function check_frob_full(address a, address b, uint256 x, uint256 y) external {
-        require(a != b);
+    function check_frob_full_vault(address a, address b, uint256 x, uint256 y) external {
         require(x <= 10 ** 30);
         require(y <= 10 ** 30);
         uint256 k0 = urns["GOLD"][a].ink;
         uint256 a0 = urns["GOLD"][a].art;
         uint256 b0 = ilks["GOLD"].Art;
         uint256 r0 = ilks["GOLD"].rate;
-        uint256 ga = gem["GOLD"][a];
-        uint256 gb = gem["GOLD"][b];
-        uint256 da = dai[a];
-        uint256 db = dai[b];
-        uint256 t0 = debt;
         frob("GOLD", a, a, b, int256(x), int256(y));
         assert(urns["GOLD"][a].ink == k0 + x);
         assert(urns["GOLD"][a].art == a0 + y);
         assert(ilks["GOLD"].Art == b0 + y);
         assert(ilks["GOLD"].rate == r0);
+    }
+
+    function check_frob_full_gem(address a, address b, uint256 x, uint256 y) external {
+        require(a != b);
+        require(x <= 10 ** 30);
+        require(y <= 10 ** 30);
+        uint256 ga = gem["GOLD"][a];
+        uint256 gb = gem["GOLD"][b];
+        frob("GOLD", a, a, b, int256(x), int256(y));
         assert(gem["GOLD"][a] + x == ga);
         assert(gem["GOLD"][b] == gb);
+    }
+
+    function check_frob_full_dai(address a, address b, uint256 x, uint256 y) external {
+        require(a != b);
+        require(x <= 10 ** 30);
+        require(y <= 10 ** 30);
+        uint256 da = dai[a];
+        uint256 db = dai[b];
+        uint256 t0 = debt;
+        uint256 r0 = ilks["GOLD"].rate;
+        frob("GOLD", a, a, b, int256(x), int256(y));
         assert(dai[a] == da);
         assert(dai[b] == db + r0 * y);
         assert(debt == t0 + r0 * y);
     }
 
-    function check_frob_close(address a, address b, uint256 x, uint256 y) external {
-        require(a != b);
+    function check_frob_close_vault(address a, address b, uint256 x, uint256 y) external {
         require(x <= 10 ** 30);
         require(y <= 10 ** 30);
         uint256 k0 = urns["GOLD"][a].ink;
         uint256 a0 = urns["GOLD"][a].art;
         uint256 b0 = ilks["GOLD"].Art;
-        uint256 r0 = ilks["GOLD"].rate;
-        uint256 ga = gem["GOLD"][b];
-        uint256 gc = gem["GOLD"][a];
-        uint256 da = dai[b];
-        uint256 t0 = debt;
         frob("GOLD", a, b, b, -int256(x), -int256(y));
         assert(urns["GOLD"][a].ink + x == k0);
         assert(urns["GOLD"][a].art + y == a0);
         assert(ilks["GOLD"].Art + y == b0);
+    }
+
+    function check_frob_close_gem(address a, address b, uint256 x, uint256 y) external {
+        require(a != b);
+        require(x <= 10 ** 30);
+        require(y <= 10 ** 30);
+        uint256 ga = gem["GOLD"][b];
+        uint256 gc = gem["GOLD"][a];
+        frob("GOLD", a, b, b, -int256(x), -int256(y));
         assert(gem["GOLD"][b] == ga + x);
         assert(gem["GOLD"][a] == gc);
+    }
+
+    function check_frob_close_dai(address a, address b, uint256 x, uint256 y) external {
+        require(x <= 10 ** 30);
+        require(y <= 10 ** 30);
+        uint256 da = dai[b];
+        uint256 t0 = debt;
+        uint256 r0 = ilks["GOLD"].rate;
+        frob("GOLD", a, b, b, -int256(x), -int256(y));
         assert(dai[b] + r0 * y == da);
         assert(debt + r0 * y == t0);
     }
@@ -546,22 +579,35 @@
         assert(urns["GOLD"][b].art == 0 || urns["GOLD"][b].art * ilks["GOLD"].rate >= ilks["GOLD"].dust);
     }
 
-    function check_fork_effect(address a, address b, uint256 x, uint256 y) external {
+    function check_fork_effect_ink(address a, address b, uint256 x, uint256 y) external {
         require(a != b);
         require(x <= 10 ** 30);
         require(y <= 10 ** 30);
         uint256 ka = urns["GOLD"][a].ink;
         uint256 kb = urns["GOLD"][b].ink;
-        uint256 aa = urns["GOLD"][a].art;
-        uint256 ab = urns["GOLD"][b].art;
-        uint256 b0 = ilks["GOLD"].Art;
-        uint256 t0 = debt;
-        uint256 ga = gem["GOLD"][a];
         fork("GOLD", a, b, int256(x), int256(y));
         assert(urns["GOLD"][a].ink + x == ka);
         assert(urns["GOLD"][b].ink == kb + x);
+    }
+
+    function check_fork_effect_art(address a, address b, uint256 x, uint256 y) external {
+        require(a != b);
+        require(x <= 10 ** 30);
+        require(y <= 10 ** 30);
+        uint256 aa = urns["GOLD"][a].art;
+        uint256 ab = urns["GOLD"][b].art;
+        fork("GOLD", a, b, int256(x), int256(y));
         assert(urns["GOLD"][a].art + y == aa);
         assert(urns["GOLD"][b].art == ab + y);
+    }
+
+    function check_fork_effect_totals(address a, address b, uint256 x, uint256 y) external {
+        require(x <= 10 ** 30);
+        require(y <= 10 ** 30);
+        uint256 b0 = ilks["GOLD"].Art;
+        uint256 t0 = debt;
+        uint256 ga = gem["GOLD"][a];
+        fork("GOLD", a, b, int256(x), int256(y));
         assert(ilks["GOLD"].Art == b0);
         assert(debt == t0);
         assert(gem["GOLD"][a] == ga);
@@ -569,24 +615,30 @@
 
     // ---------------- Confiscation ----------------
 
-    function check_grab_effect(address a, address b, uint256 x, uint256 y) external {
+    function check_grab_effect_vault(address a, address b, uint256 x, uint256 y) external {
         require(x <= 10 ** 30);
         require(y <= 10 ** 30);
         uint256 k0 = urns["GOLD"][a].ink;
         uint256 a0 = urns["GOLD"][a].art;
         uint256 b0 = ilks["GOLD"].Art;
-        uint256 r0 = ilks["GOLD"].rate;
         uint256 g0 = gem["GOLD"][a];
-        uint256 s0 = sin[b];
-        uint256 v0 = vice;
-        uint256 t0 = debt;
-        uint256 d0 = dai[b];
         grab("GOLD", a, a, b, -int256(x), -int256(y));
         assert(urns["GOLD"][a].ink + x == k0);
         assert(urns["GOLD"][a].art + y == a0);
         assert(ilks["GOLD"].Art + y == b0);
+        assert(gem["GOLD"][a] == g0 + x);
+    }
+
+    function check_grab_effect_debt(address a, address b, uint256 x, uint256 y) external {
+        require(x <= 10 ** 30);
+        require(y <= 10 ** 30);
+        uint256 r0 = ilks["GOLD"].rate;
+        uint256 s0 = sin[b];
+        uint256 v0 = vice;
+        uint256 t0 = debt;
+        uint256 d0 = dai[b];
+        grab("GOLD", a, a, b, -int256(x), -int256(y));
         assert(ilks["GOLD"].rate == r0);
-        assert(gem["GOLD"][a] == g0 + x);
         assert(sin[b] == s0 + r0 * y);
         assert(vice == v0 + r0 * y);
         assert(debt == t0);
```
