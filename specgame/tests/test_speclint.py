"""speclint: one accepted spec, and a negative case per SPEC_FORMAT rule."""
import unittest

from tests._util import TOKEN, core, speclint

GOOD = """// SPDX-License-Identifier: MIT
pragma solidity 0.8.35;

import "./CappedToken.sol";

/// A comment may say anything: this.call(), assembly, revert, balanceOf[a] = 0.
contract Spec is CappedToken {
    constructor(uint256 cap_) CappedToken(cap_) {}

    function check_mint(address a, address b, uint256 x, uint256 y) external {
        require(msg.sender == owner);
        require(x <= type(uint256).max - totalSupply);
        uint256 before = totalSupply;
        uint256 bb = balanceOf[b];
        mint(a, x);
        assert(totalSupply == before + x);
        if (a != b) {
            assert(balanceOf[b] == bb);
        }
    }

    function check_cap(address a, address b, uint256 x, uint256 y) external {
        assert(totalSupply <= cap);
    }
}
"""


def body(check_body: str, extra_members: str = "") -> str:
    return GOOD.replace("    function check_cap", extra_members + "    function check_cap").replace(
        "        assert(totalSupply <= cap);", check_body)


class SpecLint(unittest.TestCase):
    def rules(self, text: str) -> set[str]:
        return {v.rule for v in speclint.lint_spec(text)}

    def assertFlags(self, text: str, rule: str):
        rules = self.rules(text)
        self.assertIn(rule, rules, f"expected {rule}, got {rules}")

    def test_good_spec_is_clean(self):
        self.assertEqual(speclint.lint_spec(GOOD), [])

    def test_smoke_harness_is_clean(self):
        from tests._util import TAUTOLOGY
        self.assertEqual(speclint.lint_spec(TAUTOLOGY.read_text()), [])

    def test_names_from_compiled_artifact(self):
        e = core.compile_artifact(TOKEN)
        names = speclint.ArtifactNames(e["state_variables"], e["public_functions"], e["internal_functions"])
        self.assertEqual(names, speclint.DEFAULT_NAMES)

    def test_S1_pragma(self):
        self.assertFlags(GOOD.replace("pragma solidity 0.8.35;", "pragma solidity ^0.8.0;"), "S1")
        self.assertFlags(GOOD.replace("pragma solidity 0.8.35;", "pragma solidity 0.8.35;\npragma abicoder v2;"), "S1")

    def test_S2_import(self):
        self.assertFlags(GOOD.replace('import "./CappedToken.sol";', 'import "./Other.sol";'), "S2")
        self.assertFlags(GOOD.replace('import "./CappedToken.sol";',
                                     'import "./CappedToken.sol";\nimport "./Helper.sol";'), "S2")

    def test_S3_one_contract(self):
        self.assertFlags(GOOD + "\ncontract Helper { }\n", "S3")
        self.assertFlags(GOOD.replace("contract Spec is CappedToken {", "contract Spec {"), "S3")
        self.assertFlags(GOOD + "\ninterface IX { function f() external; }\n", "S3")

    def test_S4_members(self):
        self.assertFlags(body("        assert(totalSupply <= cap);", "    uint256 shadowSupply;\n"), "S4")
        self.assertFlags(body("        assert(totalSupply <= cap);",
                             "    function mint(address to, uint256 amount) public override {}\n"), "S4")
        self.assertFlags(body("        assert(totalSupply <= cap);",
                             "    function helper() internal view returns (uint256) { return cap; }\n"), "S4")
        self.assertFlags(GOOD.replace("uint256 x, uint256 y) external {\n        assert(totalSupply <= cap)",
                                     "uint256 x) external {\n        assert(totalSupply <= cap)"), "S4")
        self.assertFlags(GOOD.replace("CappedToken(cap_) {}", "CappedToken(1000) {}").replace(
            "constructor(uint256 cap_)", "constructor(uint256 cap_)"), "S4")

    def test_S5_forbidden_tokens(self):
        for stmt in ["assembly { let z := 1 }", "uint256 t = block.timestamp;", "revert();",
                     "for (uint256 i = 0; i < 2; i++) { }", "delete balanceOf[a];"]:
            self.assertIn("S5", self.rules(body(stmt + "\n        assert(totalSupply <= cap);")), stmt)

    def test_S6_member_access_external_calls(self):
        self.assertFlags(body("        assert(this.totalSupply() <= cap);"), "S6")
        self.assertFlags(body("        (bool ok, ) = address(a).call(\"\");\n        assert(ok || totalSupply <= cap);"), "S6")
        self.assertFlags(body("        assert(a.balance >= 0 || totalSupply <= cap);"), "S6")

    def test_S7_no_write_or_shadow_of_token_state(self):
        self.assertFlags(body("        totalSupply = 0;\n        assert(totalSupply <= cap);"), "S7")
        self.assertFlags(body("        balanceOf[a] += 1;\n        assert(totalSupply <= cap);"), "S7")
        self.assertFlags(body("        totalSupply++;\n        assert(totalSupply <= cap);"), "S7")
        self.assertFlags(body("        uint256 cap = 5;\n        assert(totalSupply <= cap);"), "S7")

    def test_S8_calls(self):
        self.assertFlags(body("        _mintRaw(a, x);\n        assert(totalSupply <= cap);"), "S8")
        self.assertFlags(body("        onlyOwner();\n        assert(totalSupply <= cap);"), "S8")
        self.assertFlags(body("        assert(keccak256(\"\") != 0 || totalSupply <= cap);"), "S8")

    def test_S9_body_shape(self):
        self.assertFlags(body("        mint(a, x);\n        require(x > 0);\n        assert(totalSupply <= cap);"), "S9")
        self.assertFlags(body("        mint(a, x);"), "S9")  # no assert
        self.assertFlags(body("        assert(totalSupply <= cap); assert(x == x);"), "S9")
        self.assertFlags(body("        bool t = true; assert(t || totalSupply <= cap);"), "S9")
        self.assertFlags(body("        assert(x == x);"), "S9")  # observes no token state

    def test_pre_probe_insertion(self):
        probed = speclint.pre_probe_source(GOOD, "check_mint")
        lines = probed.splitlines()
        i = next(k for k, l in enumerate(lines) if "SPECGAME-PRE-PROBE" in l)
        self.assertIn("require(x <= type(uint256).max - totalSupply);", lines[i - 1])
        self.assertIn("uint256 before = totalSupply;", lines[i + 1])
        probed = speclint.pre_probe_source(GOOD, "check_cap")
        self.assertIn("external {\n        assert(false); // SPECGAME-PRE-PROBE", probed)


class ArtifactLint(unittest.TestCase):
    def rules(self, text: str) -> set[str]:
        return {v.rule for v in speclint.lint_artifact(text)}

    def test_placeholder_is_clean(self):
        self.assertEqual(speclint.lint_artifact(TOKEN.read_text()), [])

    def test_A1_pragma(self):
        self.assertIn("A1", self.rules(TOKEN.read_text().replace("pragma solidity 0.8.35;", "pragma solidity ^0.6.12;")))
        self.assertNotIn("A1", self.rules(TOKEN.read_text().replace("pragma solidity 0.8.35;", "pragma solidity >=0.8.0;")))

    def test_A2_single_contract(self):
        self.assertIn("A2", self.rules(TOKEN.read_text() + "\nlibrary L { }\n"))
        self.assertIn("A2", self.rules(TOKEN.read_text().replace("contract CappedToken {", "contract Token {")))

    def test_A3_forbidden(self):
        t = TOKEN.read_text()
        self.assertIn("A3", self.rules(t.replace("public onlyOwner {", "external onlyOwner {")))
        self.assertIn("A3", self.rules(t.replace("totalSupply += amount;", "totalSupply += amount;\n        assert(totalSupply <= cap);")))
        self.assertIn("A3", self.rules(t.replace("uint256 public cap;", "uint256 public immutable cap;")))

    def test_A4_custom_errors(self):
        t = TOKEN.read_text().replace('require(msg.sender == owner, "not owner");',
                                      'if (msg.sender != owner) revert NotOwner();')
        self.assertIn("A4", self.rules(t))

    def test_A5_constructor(self):
        t = TOKEN.read_text().replace("constructor(uint256 cap_)", "constructor(uint256 cap_, address o)")
        self.assertIn("A5", self.rules(t))


if __name__ == "__main__":
    unittest.main()
