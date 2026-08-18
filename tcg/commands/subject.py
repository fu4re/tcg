"""`tcg subject set --runtime <path> [--environment <path>]` — install the
subject bytecode and its environment class.

Installs `subject/runtime.bin` and `subject/environment.json`, the two files
`tcg freeze` bundles and `tcg verify` step 2 (identity) checks against the
on-chain code hash. This command never touches the chain itself — it only
stages the local files; comparing `keccak(runtime.bin)` against on-chain code
is the verifier's own action (see the trust manifest freeze writes).

`--runtime` accepts either raw bytecode bytes, or a text file holding a
0x-prefixed or plain hex string (either decodes to the same raw bytes).
`--environment` must parse as JSON; if omitted and none exists yet, a
skeleton with the documented null fields is written (bundle-spec.md §2).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from tcg.outcome import Exit
from tcg.workspace import WorkspaceError, find_root, write_json

_HEX = re.compile(r"[0-9a-fA-F]+")

# The environment class documented in docs/bundle-spec.md §2: chainid, fork,
# fee schedule, constructor args / immutables, external code the claims
# assume is present.
ENVIRONMENT_SKELETON = {
    "chainid": None,
    "fork": None,
    "fee_schedule": None,
    "constructor_args": None,
    "immutables": None,
    "external_code": None,
}


def _decode_runtime(data: bytes) -> tuple[bytes, str]:
    """(bytes, note). A 0x-prefixed or plain-hex ASCII text file decodes to
    raw bytes; anything else (including actual raw bytecode, which is not
    valid ASCII in general) is installed exactly as given."""
    try:
        text = data.decode("ascii").strip()
    except UnicodeDecodeError:
        return data, "raw bytes"
    prefixed = text.lower().startswith("0x")
    body = text[2:] if prefixed else text
    if body and _HEX.fullmatch(body) and len(body) % 2 == 0:
        return bytes.fromhex(body), "decoded from hex text"
    if prefixed:
        raise ValueError("looks 0x-prefixed but is not valid hex "
                          "(odd length or non-hex characters)")
    return data, "raw bytes"


def run(args) -> int:
    if getattr(args, "subject_command", None) != "set":
        print("usage: tcg subject set --runtime <path> [--environment <path>]",
              file=sys.stderr)
        return int(Exit.USAGE)

    try:
        root = find_root()
    except WorkspaceError as e:
        print(f"tcg: {e}", file=sys.stderr)
        return int(Exit.USAGE)

    # Validate everything before writing anything: a bad --environment must
    # not leave a half-applied `subject/` (runtime.bin written, environment
    # untouched) behind for a later step to trip over silently.
    runtime_path = Path(args.runtime)
    try:
        raw = runtime_path.read_bytes()
    except OSError as e:
        print(f"tcg: cannot read --runtime {runtime_path}: {e}", file=sys.stderr)
        return int(Exit.USAGE)

    try:
        decoded, note = _decode_runtime(raw)
    except ValueError as e:
        print(f"tcg: --runtime {runtime_path}: {e}", file=sys.stderr)
        return int(Exit.USAGE)

    if not decoded:
        print(f"tcg: --runtime {runtime_path} decodes to 0 bytes; "
              "check the file contents", file=sys.stderr)
        return int(Exit.USAGE)

    env: dict | None = None
    if args.environment:
        src = Path(args.environment)
        try:
            text = src.read_text(encoding="utf-8")
        except OSError as e:
            print(f"tcg: cannot read --environment {src}: {e}", file=sys.stderr)
            return int(Exit.USAGE)
        try:
            env = json.loads(text)
        except ValueError as e:
            print(f"tcg: --environment {src} is not valid JSON: {e}", file=sys.stderr)
            return int(Exit.USAGE)

    subject_dir = root / "subject"
    subject_dir.mkdir(parents=True, exist_ok=True)
    (subject_dir / "runtime.bin").write_bytes(decoded)
    print(f"installed subject/runtime.bin ({len(decoded)} byte(s), {note})")

    env_path = subject_dir / "environment.json"
    if env is not None:
        write_json(env_path, env)
        print("installed subject/environment.json")
    elif not env_path.is_file():
        write_json(env_path, ENVIRONMENT_SKELETON)
        print("installed subject/environment.json (skeleton — fill in chainid, "
              "fork, fee_schedule, constructor_args, immutables, external_code)")
    else:
        print("subject/environment.json already present; left unchanged "
              "(pass --environment <path> to replace it)")

    print("note: freeze bundles these files; `tcg verify` step 2 compares "
          "keccak(subject/runtime.bin) against the on-chain code hash — that "
          "comparison is not made here")
    return int(Exit.OK)
