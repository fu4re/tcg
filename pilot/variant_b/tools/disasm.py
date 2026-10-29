#!/usr/bin/env python3
"""Disassemble the GemJoin ETH-A runtime and trace the ilk()/vat() paths.

Usage: python3 -I tools/disasm.py <runtime.hex> [selector-hex ...]

Prints (1) the keccak/size check, (2) the opcode histogram of the whole
runtime (code region before the 0xfe/metadata tail is reported separately),
(3) for each selector, the concrete instruction trace of a call with
calldata = selector, callvalue = 0, simulated on a tiny stack machine with
storage values left symbolic. The trace is only used to list the opcodes on
the path; the verdict comes from the Lean proof, not from this script.
"""
import sys

OPS = {
    0x00: "STOP", 0x01: "ADD", 0x02: "MUL", 0x03: "SUB", 0x04: "DIV", 0x05: "SDIV",
    0x06: "MOD", 0x07: "SMOD", 0x08: "ADDMOD", 0x09: "MULMOD", 0x0a: "EXP",
    0x0b: "SIGNEXTEND", 0x10: "LT", 0x11: "GT", 0x12: "SLT", 0x13: "SGT",
    0x14: "EQ", 0x15: "ISZERO", 0x16: "AND", 0x17: "OR", 0x18: "XOR", 0x19: "NOT",
    0x1a: "BYTE", 0x1b: "SHL", 0x1c: "SHR", 0x1d: "SAR", 0x20: "KECCAK256",
    0x30: "ADDRESS", 0x31: "BALANCE", 0x32: "ORIGIN", 0x33: "CALLER",
    0x34: "CALLVALUE", 0x35: "CALLDATALOAD", 0x36: "CALLDATASIZE",
    0x37: "CALLDATACOPY", 0x38: "CODESIZE", 0x39: "CODECOPY", 0x3a: "GASPRICE",
    0x3b: "EXTCODESIZE", 0x3c: "EXTCODECOPY", 0x3d: "RETURNDATASIZE",
    0x3e: "RETURNDATACOPY", 0x3f: "EXTCODEHASH", 0x40: "BLOCKHASH",
    0x41: "COINBASE", 0x42: "TIMESTAMP", 0x43: "NUMBER", 0x44: "PREVRANDAO",
    0x45: "GASLIMIT", 0x46: "CHAINID", 0x47: "SELFBALANCE", 0x48: "BASEFEE",
    0x49: "BLOBHASH", 0x4a: "BLOBBASEFEE", 0x50: "POP", 0x51: "MLOAD",
    0x52: "MSTORE", 0x53: "MSTORE8", 0x54: "SLOAD", 0x55: "SSTORE", 0x56: "JUMP",
    0x57: "JUMPI", 0x58: "PC", 0x59: "MSIZE", 0x5a: "GAS", 0x5b: "JUMPDEST",
    0x5c: "TLOAD", 0x5d: "TSTORE", 0x5e: "MCOPY", 0x5f: "PUSH0",
    0xa0: "LOG0", 0xa1: "LOG1", 0xa2: "LOG2", 0xa3: "LOG3", 0xa4: "LOG4",
    0xf0: "CREATE", 0xf1: "CALL", 0xf2: "CALLCODE", 0xf3: "RETURN",
    0xf4: "DELEGATECALL", 0xf5: "CREATE2", 0xfa: "STATICCALL", 0xfd: "REVERT",
    0xfe: "INVALID", 0xff: "SELFDESTRUCT",
}
for i in range(1, 33):
    OPS[0x5f + i] = f"PUSH{i}"
for i in range(1, 17):
    OPS[0x7f + i] = f"DUP{i}"
    OPS[0x8f + i] = f"SWAP{i}"


def name(b):
    return OPS.get(b, f"UNDEFINED(0x{b:02x})")


def decode(code):
    pc, out = 0, []
    while pc < len(code):
        b = code[pc]
        n = b - 0x5f if 0x60 <= b <= 0x7f else 0
        arg = int.from_bytes(code[pc + 1:pc + 1 + n].ljust(n, b"\0"), "big") if n else None
        out.append((pc, b, arg))
        pc += 1 + n
    return out


M = 2**256


def trace(code, selector):
    """Concrete run with symbolic storage words (strings). Returns list of (pc, op)."""
    ins = {pc: (b, a) for pc, b, a in decode(code)}
    jd = {pc for pc, (b, _) in ins.items() if b == 0x5b}
    calldata = selector.to_bytes(4, "big")
    st, mem, pc, path = [], {}, 0, []

    def cd(off):
        return int.from_bytes(calldata[off:off + 32].ljust(32, b"\0"), "big") if off < len(calldata) else 0

    while True:
        b, a = ins[pc]
        op = name(b)
        path.append((pc, op))
        nxt = pc + 1 + (b - 0x5f if 0x60 <= b <= 0x7f else 0)
        if op.startswith("PUSH"):
            st.append(a or 0)
        elif op.startswith("DUP"):
            st.append(st[-int(op[3:])])
        elif op.startswith("SWAP"):
            k = int(op[4:]); st[-1], st[-1 - k] = st[-1 - k], st[-1]
        elif op == "POP":
            st.pop()
        elif op == "JUMPDEST":
            pass
        elif op == "CALLVALUE":
            st.append(0)
        elif op == "CALLDATASIZE":
            st.append(len(calldata))
        elif op == "CALLDATALOAD":
            st.append(cd(st.pop()))
        elif op in ("ISZERO",):
            x = st.pop(); st.append(int(x == 0))
        elif op in ("LT", "GT", "EQ", "SHR", "SUB", "ADD", "AND", "SHL"):
            x = st.pop(); y = st.pop()
            if isinstance(x, str) or isinstance(y, str):
                if op == "AND":
                    st.append(f"({x}&{y})")
                else:
                    raise RuntimeError(f"symbolic {op} at {pc:#x}")
            else:
                st.append({"LT": int(x < y), "GT": int(x > y), "EQ": int(x == y),
                           "SHR": (y >> x) % M, "SUB": (x - y) % M, "ADD": (x + y) % M,
                           "AND": x & y, "SHL": (y << x) % M}[op])
        elif op == "EXP":
            x = st.pop(); y = st.pop(); st.append(pow(x, y, M))
        elif op == "DIV":
            x = st.pop(); y = st.pop()
            st.append(f"({x}/{y})" if isinstance(x, str) else (x // y if y else 0))
        elif op == "SLOAD":
            st.append(f"S[{st.pop()}]")
        elif op == "MSTORE":
            off = st.pop(); v = st.pop(); mem[off] = v
        elif op == "MLOAD":
            st.append(mem.get(st.pop(), 0))
        elif op == "JUMP":
            t = st.pop(); assert t in jd, hex(t); pc = t; continue
        elif op == "JUMPI":
            t = st.pop(); c = st.pop()
            if c:
                assert t in jd, hex(t); pc = t; continue
        elif op in ("RETURN", "REVERT", "STOP", "INVALID"):
            return path, op, st, mem
        else:
            raise RuntimeError(f"unhandled {op} at {pc:#x}")
        pc = nxt


def main():
    h = open(sys.argv[1]).read().strip()
    h = h[2:] if h.startswith("0x") else h
    code = bytes.fromhex(h)
    print(f"size {len(code)} bytes")
    try:
        from Crypto.Hash import keccak  # pycryptodome
        print("keccak256 0x" + keccak.new(digest_bits=256, data=code).hexdigest())
    except ImportError:
        print("keccak256: pycryptodome not available, not checked here")
    ins = decode(code)
    # Solidity 0.5 metadata: the code region ends at the first 0xfe that
    # directly precedes the a165/a265 CBOR marker.
    meta = code.rfind(bytes.fromhex("fea265627a7a7231"))
    print(f"code region [0, {meta:#x}] (INVALID at {meta:#x}), metadata tail {len(code) - meta - 1} bytes")
    hist, hist_meta = {}, {}
    for pc, b, a in ins:
        (hist if pc <= meta else hist_meta)[name(b)] = (hist if pc <= meta else hist_meta).get(name(b), 0) + 1
    print("opcodes in code region:", len(hist))
    for k in sorted(hist):
        print(f"  {k:14s} {hist[k]}")
    print("byte values decoded in metadata tail (never executed):", sorted(hist_meta))
    for s in sys.argv[2:]:
        path, how, st, mem = trace(code, int(s, 16))
        ops = sorted({op for _, op in path})
        print(f"\nselector {s}: {len(path)} instructions, ends in {how}, final stack {st}, mem {mem}")
        print("  distinct opcodes:", " ".join(ops))
        print("  trace:", " ".join(f"{pc:x}:{op}" for pc, op in path))


if __name__ == "__main__":
    main()
