# Round 2 -> 3 weakening diffs (grab checks)

## fM/seed_0

`runs/v3/vat/fM/seed_0/round_2/cand_2/Spec.sol` (check_grab_sin_up, check_grab_sin_down) -> `runs/v3/vat/fM/seed_0/round_3/cand_2/Spec.sol` (check_grab_debt_unchanged)

```diff
--- runs/v3/vat/fM/seed_0/round_2/cand_2/Spec.sol
+++ runs/v3/vat/fM/seed_0/round_3/cand_2/Spec.sol
@@ -1,21 +1,5 @@
-function check_grab_sin_up(bytes32 i, address u, int256 dx, int256 dy) external {
-        require(dy == -1);
-        uint256 s0 = sin[u];
-        uint256 v0 = vice;
+function check_grab_debt_unchanged(bytes32 i, address u, int256 dx, int256 dy) external {
         uint256 t0 = debt;
-        uint256 r0 = ilks[i].rate;
         grab(i, u, u, u, dx, dy);
-        assert(sin[u] == s0 + r0);
-        assert(vice == v0 + r0);
         assert(debt == t0);
     }
-
-function check_grab_sin_down(bytes32 i, address u, int256 dx, int256 dy) external {
-        require(dy == 1);
-        uint256 s0 = sin[u];
-        uint256 v0 = vice;
-        uint256 r0 = ilks[i].rate;
-        grab(i, u, u, u, dx, dy);
-        assert(sin[u] + r0 == s0);
-        assert(vice + r0 == v0);
-    }
```

## f0/seed_0

`runs/v3/vat/f0/seed_0/round_2/cand_1/Spec.sol` (check_grab_sin) -> `runs/v3/vat/f0/seed_0/round_3/cand_1/Spec.sol` (check_grab_sin_up)

```diff
--- runs/v3/vat/f0/seed_0/round_2/cand_1/Spec.sol
+++ runs/v3/vat/f0/seed_0/round_3/cand_1/Spec.sol
@@ -1,15 +1,15 @@
-function check_grab_sin(bytes32 i, address u, int256 dx, int256 dy) external {
+function check_grab_sin_up(bytes32 i, address u, int256 dx, int256 dy) external {
         require(wards[msg.sender] == 1);
-        require(dx <= 0 && dx > -(2**100));
-        require(dy <= 0 && dy > -(2**100));
+        require(dx >= 0 && dx < 2**100);
+        require(dy >= 0 && dy < 2**100);
         require(ilks[i].rate == 10**27);
         require(sin[u] < 2**128);
         require(vice < 2**128);
         uint256 s0 = sin[u];
         uint256 v0 = vice;
         uint256 t0 = debt;
         grab(i, u, u, u, dx, dy);
         assert(int256(sin[u]) == int256(s0) - dy * 10**27);
         assert(int256(vice) == int256(v0) - dy * 10**27);
         assert(debt == t0);
     }
```

