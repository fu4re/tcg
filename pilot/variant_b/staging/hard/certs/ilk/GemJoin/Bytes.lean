import EvmYul.Wheels

/-!
# The 32-byte big-endian layout of `UInt256.toByteArray`

Lemmas that justify the kernel-transparency patches 0003, 0004 and 0005 of the
vendored EVMYulLean: each patched definition equals the upstream expression.
-/

namespace GemJoin
open EvmYul

/-- The 32 big-endian bytes of a word: element `j` is `v / 256^(31-j) mod 256`. -/
def bytes32 (n : ℕ) : List UInt8 :=
  ((List.range 32).map fun i => UInt8.ofNat (n / 256 ^ i)).reverse

/-- `k` little-endian bytes of `n`. -/
def leBytes (k n : ℕ) : List UInt8 :=
  (List.range k).map fun i => UInt8.ofNat (n / 256 ^ i)

open private toBytes' from EvmYul.UInt256

theorem toBytes'_zero : toBytes' 0 = [] := by unfold toBytes'; rfl

theorem toBytes'_succ (n : ℕ) :
    toBytes' (n + 1) = UInt8.ofNat (n + 1) :: toBytes' ((n + 1) / 256) := by
  rw [toBytes']
  congr 1

theorem leBytes_succ (k n : ℕ) :
    leBytes (k + 1) n = UInt8.ofNat n :: leBytes k (n / 256) := by
  simp only [leBytes, List.range_succ_eq_map, List.map_cons, List.map_map]
  congr 1
  · simp
  · apply List.map_congr_left
    intro i _
    simp [Function.comp, Nat.div_div_eq_div_mul, pow_succ, mul_comm]

/-- Patch 0004's structural `toBytesFuel` agrees with upstream's `toBytes'`
whenever the fuel is at least `n`. -/
theorem toBytesFuel_eq : ∀ (fuel n : ℕ), n ≤ fuel → toBytesFuel fuel n = toBytes' n
  | 0, n, h => by
    have : n = 0 := by omega
    subst this; rw [toBytes'_zero]; rfl
  | fuel + 1, 0, _ => by rw [toBytes'_zero]; rfl
  | fuel + 1, n + 1, h => by
    rw [toBytes'_succ, toBytesFuel, toBytesFuel_eq fuel _
      (Nat.lt_succ_iff.mp (lt_of_lt_of_le (Nat.div_lt_self (Nat.succ_pos n) (by decide)) h))]
    congr 1

theorem toBytes'_pad (k : ℕ) : ∀ n, n < 256 ^ k →
    toBytes' n ++ List.replicate (k - (toBytes' n).length) 0 = leBytes k n := by
  induction k with
  | zero =>
    intro n h
    have : n = 0 := by simpa using h
    subst this
    simp [toBytes'_zero, leBytes]
  | succ k ih =>
    intro n h
    cases n with
    | zero =>
      rw [toBytes'_zero, leBytes_succ]
      have h0 := ih 0 (by positivity)
      rw [toBytes'_zero] at h0
      simp only [List.nil_append, List.length_nil, Nat.sub_zero] at h0 ⊢
      rw [List.replicate_succ, Nat.zero_div, ← h0]
      rfl
    | succ n =>
      have hlt : (n + 1) / 256 < 256 ^ k := by
        rw [Nat.div_lt_iff_lt_mul (by norm_num)]
        simpa [pow_succ] using h
      rw [toBytes'_succ, leBytes_succ, ← ih _ hlt]
      simp

theorem toByteArray_loop (l : List UInt8) (r : ByteArray) :
    List.toByteArray.loop l r = ⟨r.data ++ l.toArray⟩ := by
  induction l generalizing r with
  | nil => simp [List.toByteArray.loop]
  | cons b bs ih =>
    simp only [List.toByteArray.loop, ih]
    simp [ByteArray.push]

theorem data_append (a b : ByteArray) : (a ++ b).data = a.data ++ b.data := by
  show (b.copySlice 0 a a.size b.size false).data = _
  simp only [ByteArray.copySlice, ByteArray.size, Nat.zero_add, Nat.sub_zero, Nat.min_self,
    Array.extract_size]
  have : a.data.extract (a.data.size + b.data.size) = #[] := by
    apply Array.eq_empty_of_size_eq_zero; simp
  simp [this]

theorem ext' {a b : ByteArray} (h : a.data = b.data) : a = b := by
  cases a; cases b; cases h; rfl

/-- Faithfulness of patch 0005: upstream's `UInt256.toByteArray v`
(`zeroes (32 - b.size) ++ b` with `b := BE v.toNat`) equals the patched definition,
the 32 big-endian bytes written elementwise. -/
theorem toByteArray_eq (v : UInt256) :
    ffi.ByteArray.zeroes (32 - (BE v.toNat).size) ++ BE v.toNat = UInt256.toByteArray v := by
  have hv : v.toNat < 256 ^ 32 := by
    have := v.val.isLt
    simp only [UInt256.toNat, UInt256.size] at this ⊢
    omega
  have hpad := congrArg List.reverse (toBytes'_pad 32 v.toNat hv)
  simp only [List.reverse_append, List.reverse_replicate] at hpad
  show _ = (⟨(bytes32 v.toNat).toArray⟩ : ByteArray)
  apply ext'
  rw [data_append]
  simp only [BE, Function.comp, toBytesBigEndian, toBytesFuel_eq _ _ (le_refl _), List.toByteArray,
    toByteArray_loop, ffi.ByteArray.zeroes, ByteArray.size]
  rw [bytes32, ← leBytes, ← hpad]
  simp [ByteArray.empty, ByteArray.emptyWithCapacity]

/-! ## Faithfulness of patch 0003

Patch 0003 replaces `b.toList` (Lean core, a well-founded loop) by
`b.data.toList` in `fromByteArrayBigEndian`. The two lists are equal. -/

theorem toList_loop (b : ByteArray) :
    ∀ (k i : ℕ) (r : List UInt8), b.size - i = k →
      ByteArray.toList.loop b i r = r.reverse ++ b.data.toList.drop i := by
  intro k
  induction k with
  | zero =>
    intro i r hk
    unfold ByteArray.toList.loop
    have hi : ¬ i < b.size := by omega
    simp only [hi, if_false]
    have : b.data.toList.drop i = [] := by
      apply List.drop_eq_nil_of_le; simp [ByteArray.size] at hk ⊢; omega
    simp [this]
  | succ k ih =>
    intro i r hk
    unfold ByteArray.toList.loop
    have hi : i < b.size := by omega
    simp only [hi, if_true]
    rw [ih (i + 1) _ (by omega)]
    have hd : b.data.toList.drop i = b.data[i]'hi :: b.data.toList.drop (i + 1) := by
      rw [List.drop_eq_getElem_cons (by simpa [ByteArray.size] using hi)]
      simp
    rw [hd]
    have hi' : i < b.data.size := hi
    simp [ByteArray.get!, Array.getElem!_eq_getD, Array.getD, hi']

theorem ByteArray_toList_eq (b : ByteArray) : b.toList = b.data.toList := by
  unfold ByteArray.toList
  rw [toList_loop b (b.size - 0) 0 [] rfl]
  simp

end GemJoin
