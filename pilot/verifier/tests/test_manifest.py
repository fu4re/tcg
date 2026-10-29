"""Task 01 done-when, by test: the example validates; the linter rejects a
`verdict` key; the linter rejects a root_hash computed over a different child
list. Plus the remaining manifest rules and schema hygiene."""
from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest

import helpers
from helpers import toy
from tcgverify import canon
from tcgverify.jsonschema_min import SchemaError, validate

PILOT = os.path.dirname(os.path.dirname(helpers.HERE))
LINT = os.path.join(PILOT, "tools", "lint_manifest.py")
EXAMPLE = os.path.join(PILOT, "schema", "examples", "manifest.example.json")


def lint(path, *flags):
    return subprocess.run([sys.executable, LINT, path, *flags], capture_output=True, text=True)


class ExampleAndLinter(unittest.TestCase):
    def setUp(self):
        with open(EXAMPLE, encoding="utf-8") as f:
            self.example = json.load(f)
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def lint_obj(self, obj, rehash=True):
        if rehash:
            obj["root_hash"] = canon.root_hash(obj)
        p = os.path.join(self.tmp.name, "manifest.json")
        with open(p, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False)
        return lint(p, "--schema-only")

    def test_example_validates(self):
        r = lint(EXAMPLE, "--schema-only")
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_rejects_verdict_key(self):
        m = copy.deepcopy(self.example)
        m["verdict"] = "accept"
        r = self.lint_obj(m)  # root_hash recomputed, so only the key can fail it
        self.assertEqual(r.returncode, 1)
        self.assertIn("$.verdict: forbidden key", r.stdout)

    def test_rejects_forbidden_key_nested(self):
        for key in ("level", "proved", "pass", "L1", "score"):
            m = copy.deepcopy(self.example)
            m["children"][0][key] = 1
            r = self.lint_obj(m)
            self.assertEqual(r.returncode, 1, key)
            self.assertIn("forbidden key", r.stdout)

    def test_rejects_word_proved_in_values(self):
        m = copy.deepcopy(self.example)
        m["self_contained_reason"] = "all claims proved by KEVM"
        r = self.lint_obj(m)
        self.assertEqual(r.returncode, 1)
        self.assertIn("proved", r.stdout)

    def test_rejects_root_hash_over_different_child_list(self):
        m = copy.deepcopy(self.example)
        other = copy.deepcopy(m)
        other["children"] = other["children"][:-1]
        m["root_hash"] = canon.root_hash(other)
        r = self.lint_obj(m, rehash=False)
        self.assertEqual(r.returncode, 1)
        self.assertIn("root_hash mismatch", r.stdout)

    def test_root_hash_excludes_only_root_and_signature(self):
        m = copy.deepcopy(self.example)
        before = canon.root_hash(m)
        m["producer_sig"]["sig"] = "00" * 64
        self.assertEqual(canon.root_hash(m), before)
        m["self_contained"] = True
        self.assertNotEqual(canon.root_hash(m), before)

    def test_canonical_json_is_utf8_sorted_compact(self):
        self.assertEqual(canon.canonical({"b": 1, "a": "φ"}), '{"a":"φ","b":1}'.encode("utf-8"))
        with self.assertRaises(ValueError):
            canon.canonical({"x": 1.5})

    def test_schema_rules(self):
        cases = {
            "not_claimed altered": lambda m: m["not_claimed"].__setitem__(0, "The artefact is secure."),
            "not_claimed missing a sentence": lambda m: m["not_claimed"].pop(),
            "self_contained false without reason": lambda m: m.pop("self_contained_reason"),
            "self_contained not boolean": lambda m: m.__setitem__("self_contained", "no"),
            "evidence labelled T": lambda m: m["children"][-3].__setitem__("class", "T"),
            "provenance labelled T": lambda m: m["children"][-1].__setitem__("class", "T"),
            "unknown role": lambda m: m["children"][0].__setitem__("role", "proof"),
            "two artefacts": lambda m: m["children"].append(dict(m["children"][0], path="hard/b2.bin")),
            "no checker": lambda m: m.__setitem__("children", [c for c in m["children"] if c["role"] != "checker"]),
            "no T_hat": lambda m: m.__setitem__("children", [c for c in m["children"] if c["role"] != "T_hat"]),
            "c without claim": lambda m: [c.pop("claim") for c in m["children"] if c["role"] == "c"],
            "path escapes": lambda m: m["children"][0].__setitem__("path", "../etc/passwd"),
            "absolute path": lambda m: m["children"][0].__setitem__("path", "/etc/passwd"),
            "duplicate path": lambda m: m["children"].append(dict(m["children"][1])),
            "unknown top-level field": lambda m: m.__setitem__("note", "x"),
            "uppercase hash": lambda m: m["children"][0].__setitem__("hash", "A" * 64),
        }
        for name, mutate in cases.items():
            m = copy.deepcopy(self.example)
            mutate(m)
            r = self.lint_obj(m)
            self.assertEqual(r.returncode, 1, f"{name}: {r.stdout}")

    def test_vendored_schemas_identical(self):
        for name in ("manifest.schema.json", "trusted_base.schema.json", "rediscuss.schema.json"):
            with open(os.path.join(PILOT, "schema", name), "rb") as a, \
                    open(os.path.join(PILOT, "verifier", "tcgverify", name), "rb") as b:
                self.assertEqual(a.read(), b.read(), name)

    def test_validator_fails_closed_on_unknown_keyword(self):
        with self.assertRaises(SchemaError):
            validate({}, {"type": "object", "propertyNames": {"pattern": "^a"}})


class LintRealBundle(helpers.ToyCase):
    def test_toy_bundle_lints_clean(self):
        r = lint(os.path.join(self.pristine, "manifest.json"))
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_child_bytes_changed(self):
        b = self.fresh()
        with open(os.path.join(b, "hard/spec/claim-01.k"), "a") as f:
            f.write("x")
        r = lint(os.path.join(b, "manifest.json"))
        self.assertEqual(r.returncode, 1)
        self.assertIn("hard/spec/claim-01.k: sha256 differs", r.stdout)

    def test_unlisted_file(self):
        b = self.fresh()
        toy.write(b, "hard/extra.k", "TOY-PROVABLE")
        r = lint(os.path.join(b, "manifest.json"))
        self.assertIn("hard/extra.k: file in bundle dir but not listed", r.stdout)

    def test_rule2_claim_without_certificate_or_reason(self):
        b = self.fresh()
        p = os.path.join(b, "trusted_base.json")
        with open(p) as f:
            tb = json.load(f)
        tb["claims_without_certificate"] = tb["claims_without_certificate"][:1]
        toy.write_json(b, "trusted_base.json", tb)
        toy.resign(b, self.keys["producer"])
        r = lint(os.path.join(b, "manifest.json"))
        self.assertEqual(r.returncode, 1)
        self.assertIn("claim-02: no certificate and not in claims_without_certificate", r.stdout)


if __name__ == "__main__":
    unittest.main()
