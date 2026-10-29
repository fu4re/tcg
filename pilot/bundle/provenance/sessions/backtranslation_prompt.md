You are translating formal specifications into plain English. You have no tools and no other context: everything you may use is in this message, below the line "=== INPUT ===".

The input contains five K-framework reachability claims about one EVM contract's runtime bytecode (files claim-01.k to claim-05.k; the long hex strings are the bytecode), and a JSON file phi.json describing them.

Task: for each claim, write one or two plain English sentences saying what the claim states: under which starting conditions (calldata, caller, storage, callvalue, frame), what every execution is guaranteed to end with (status, output, what stays unchanged), and any restriction on the set of starting states. Base the translation on the K text first; use phi.json only to read it. Do not explain the bytecode and do not guess what the contract is for beyond what the claims say.

Do not evaluate, approve or compare the claims against any requirement or intention. You have not been given one, and any statement that the claims "match", "satisfy" or "correctly capture" an informal specification is out of scope. Do not write one.

Answer with ONLY a JSON array, no prose before or after it, of exactly five objects in claim order:
[{"claim": "claim-01", "translation": "<one or two sentences>"}, ...]
