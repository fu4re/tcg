import json, pathlib
p = pathlib.Path("hard/annotations.json")
d = json.loads(p.read_text())
anns = d["annotations"]
ids = [a["id"] for a in anns]
g = next(a for a in anns if a["id"] == "Aasm-gas-abstraction")
g["justification"] = ("Standard KEVM functional-correctness configuration. Consequence: every claim holds only for executions that do not run out of gas. "
                      "Out-of-gas is an exceptional halt (status EVMC_OUT_OF_GAS, all gas consumed), which is neither the EVMC_SUCCESS of claims 01-03 "
                      "nor the EVMC_REVERT of claims 04-05; no claim guarantees termination within any gas limit.")
new = [
    {
        "id": "Aasm-keccak-wards-slot", "class": "T", "kind": "aasm_precondition",
        "statement": "Pre conjunct #lookup(STORAGE, keccak(#buf(32, MSGSENDER) +Bytes #buf(32, 0))) ==Int 0 states wards[caller] == 0: the slot of key caller in the mapping at slot 0 under solc 0.5.12's layout keccak256(pad32(key) ++ pad32(slot)), with KEVM's keccak(Bytes) standing for Keccak-256.",
        "used_by": ["claim-04"],
        "justification": "solc's documented mapping layout and KEVM's keccak hook (blockchain-k-plugin) computing Keccak-256 on concrete bytes. During the symbolic proof keccak stays an uninterpreted function and the proof needs neither injectivity nor a concrete value; the assumption only fixes what the Pre MEANS for the deployed contract.",
        "covered_by_assumption": "A_keccak",
        "k_patterns": {"requires": ["#lookup\\(STORAGE, keccak\\(#buf\\(32, MSGSENDER\\) \\+Bytes #buf\\(32, 0\\)\\)\\) ==Int 0"]},
    },
    {
        "id": "Aasm-rangeUInt-args", "class": "T", "kind": "aasm_precondition",
        "statement": "#rangeUInt(256, USR) and #rangeUInt(256, WAD): each ABI argument word of join's calldata is in [0, 2^256).",
        "used_by": ["claim-05"],
        "justification": "A calldata word is 32 bytes, so every value it can hold is in range; #buf(32, X) is only the intended encoding for X in range. Excludes nothing a real call can send.",
        "covered_by_assumption": "Aasm-05",
        "k_patterns": {"requires": ["#rangeUInt\\(256, (USR|WAD)\\)"]},
    },
]
for n in new:
    if n["id"] in ids:
        anns[ids.index(n["id"])] = n
    else:
        anns.append(n)
p.write_text(json.dumps(d, indent=2) + "\n")
print([a["id"] for a in anns])
