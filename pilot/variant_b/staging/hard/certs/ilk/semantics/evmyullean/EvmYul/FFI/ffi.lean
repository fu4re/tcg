namespace ffi

@[extern "sha256"]
opaque sha256 (input : @& ByteArray) (len : USize) : ByteArray

def SHA256 (d : ByteArray) : Except String ByteArray :=
  pure <| sha256 d d.size.toUSize

@[extern "blake2compressb64"]
opaque BLAKE2Compress (input : @& ByteArray) : ByteArray

def BLAKE2 (d : ByteArray) : Except String ByteArray := do
  if d.size != 213                    then throw "error"
  if d[212]! ∉ [0, 1].map Nat.toUInt8 then throw "error"
  return BLAKE2Compress d

-- tcg pilot patch 0002: upstream is an `opaque` FFI constant over `USize`, which
-- the kernel cannot unfold (and `USize` literals depend on the opaque
-- `System.Platform.numBits`). Same result, n zero bytes, as a Lean definition
-- over `Nat`. Differs from the compiled upstream only for n ≥ 2^64, where the
-- C `memset_zero` would receive n mod 2^64.
def ByteArray.zeroes (n : Nat) : ByteArray := ⟨Array.replicate n 0⟩

@[extern "keccak256"]
opaque keccak256 (input : @& ByteArray) (len : USize) : ByteArray

def KECCAK256 (d : ByteArray) : Except String ByteArray :=
  pure <| keccak256 d d.size.toUSize

def KEC (data : ByteArray) : ByteArray :=
  ffi.KECCAK256 data |>.toOption.getD .empty

end ffi
