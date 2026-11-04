"""Bundle assembler (tools/bundle.py): determinism, the committed fixture is
fresh, producer-side discard, input refusals, and the stdlib schema subset."""
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

from tests._util import FIXTURES, ROOT, core

sys.path.insert(0, str(FIXTURES / "bundle"))
import bundle  # noqa: E402
import make_fixture  # noqa: E402
import verify  # noqa: E402

GOOD = FIXTURES / "bundle" / "good"


def tree(d: Path) -> dict[str, bytes]:
    return {p.relative_to(d).as_posix(): p.read_bytes() for p in sorted(d.rglob("*")) if p.is_file()}


def run_bundle(argv: list[str]) -> int:
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return bundle.main(argv)


class Assemble(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.t = Path(cls.tmp.name)
        cls.codes = [run_bundle(make_fixture.bundle_args(cls.t / f"b{i}")) for i in (1, 2)]

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_deterministic(self):
        self.assertEqual(self.codes, [0, 0])
        self.assertEqual(tree(self.t / "b1"), tree(self.t / "b2"))

    def test_committed_fixture_is_fresh(self):
        # Fails after a change to verify.py, specgame_core.py, protocol.md or the
        # fixture inputs: run `make bundle-fixture` and commit good/.
        self.assertEqual(tree(self.t / "b1"), tree(GOOD), "stale fixture: run `make bundle-fixture`")

    def test_layout_and_claims(self):
        m = json.loads((GOOD / "manifest.json").read_text())
        files = set(tree(GOOD)) - {"manifest.json"}
        self.assertEqual(set(m["files"]), files)
        for p, h in m["files"].items():
            self.assertEqual(core.sha256_file(GOOD / p), h, p)
        self.assertEqual(m["claimed"]["ms_cert"], {"killed": 2, "total": 3})
        self.assertEqual(m["not_claimed"], ["V-completeness"])
        self.assertEqual(m["hard"]["c"]["verdict"], "Accept")
        self.assertEqual(m["hard"]["c"]["mode"], "isolated")
        self.assertEqual(sorted(r["check"] for r in m["hard"]["c"]["checks"]), sorted(m["hard"]["phi"]["checks"]))
        for row in m["hard"]["c"]["checks"]:
            self.assertEqual(core.sha256_file(GOOD / row["solc_input_path"]), row["solc_input_sha256"])
            self.assertEqual(row["verdict"], "Accept")
        self.assertIsNone(m["provenance"]["feedback"])
        self.assertEqual(m["provenance"]["verifier_sha256"], core.sha256_file(ROOT / "tools" / "verify.py"))
        # The deliberately bad candidate (m01's sigma presented against m03) is
        # discarded by the producer, with its outcomes, and m03 is not killed.
        self.assertEqual(len(m["evidence"]["discarded"]), 1)
        d = m["evidence"]["discarded"][0]
        self.assertNotIn(d["witness"]["mutant"], m["claimed"]["kill_set"])
        self.assertIn("no check ends in violation", d["reason"])
        self.assertEqual(verify.SchemaValidator(verify.SCHEMA_DIR).validate(m, "manifest.schema.json"), [])

    def _mutated_inputs(self, edit) -> list[str]:
        doc = json.loads((make_fixture.INPUTS / "mutants.json").read_text())
        edit(doc)
        p = self.t / "mutants_edit.json"
        p.write_text(json.dumps(doc))
        args = make_fixture.bundle_args(self.t / "refused")
        args[args.index("--mutants") + 1] = str(p)
        return args

    def test_refuses_wrong_mutant_id(self):
        def edit(doc):
            doc["mutants"][0]["id"] = doc["mutants"][1]["id"]
        self.assertEqual(run_bundle(self._mutated_inputs(edit)), 1)
        self.assertFalse((self.t / "refused").exists())

    def test_refuses_foreign_base(self):
        def edit(doc):
            doc["base"]["runtime_sha256"] = "0" * 64
        self.assertEqual(run_bundle(self._mutated_inputs(edit)), 1)

    def test_refuses_non_separating_properness(self):
        def edit(doc):
            doc["mutants"][0]["properness"]["sigma"]["txs"] = []
        self.assertEqual(run_bundle(self._mutated_inputs(edit)), 1)


class SchemaSubset(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def v(self, schema: dict, inst) -> list[str]:
        (self.dir / "s.json").write_text(json.dumps(schema))
        return verify.SchemaValidator(self.dir).validate(inst, "s.json")

    def test_unknown_keyword_fails_closed(self):
        with self.assertRaises(verify.SchemaError):
            self.v({"type": "string", "maxLength": 3}, "abcd")

    def test_bool_is_not_integer(self):
        self.assertTrue(self.v({"type": "integer"}, True))
        self.assertTrue(self.v({"const": 1}, True))
        self.assertEqual(self.v({"const": 1}, 1), [])

    def test_oneof_contains_ref(self):
        s = {"oneOf": [{"type": "null"}, {"$ref": "#/$defs/a"}],
             "$defs": {"a": {"type": "array", "contains": {"const": "V-completeness"}}}}
        self.assertEqual(self.v(s, None), [])
        self.assertEqual(self.v(s, ["x", "V-completeness"]), [])
        self.assertTrue(self.v(s, ["x"]))

    def test_all_schemas_use_only_the_subset(self):
        allowed = verify._KEYWORDS | verify._ANNOTATIONS

        def walk(s, at):
            self.assertIsInstance(s, dict, at)
            self.assertLessEqual(set(s), allowed, f"{at}: {sorted(set(s) - allowed)}")
            for k in ("properties", "$defs"):
                for name, sub in s.get(k, {}).items():
                    walk(sub, f"{at}.{k}.{name}")
            for k in ("items", "contains", "if", "then", "else"):
                if k in s:
                    walk(s[k], f"{at}.{k}")
            if isinstance(s.get("additionalProperties"), dict):
                walk(s["additionalProperties"], f"{at}.additionalProperties")
            for k in ("oneOf", "anyOf", "allOf"):
                for i, sub in enumerate(s.get(k, [])):
                    walk(sub, f"{at}.{k}[{i}]")

        for p in sorted((ROOT / "schemas").glob("*.schema.json")):
            walk(json.loads(p.read_text()), p.name)


if __name__ == "__main__":
    unittest.main()
