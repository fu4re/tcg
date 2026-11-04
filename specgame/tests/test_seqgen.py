"""seqgen: determinism, schema validity of every σ, the documented distribution."""
import unittest

from tests._util import TOKEN, core
import seqgen

FNS = ["mint(address,uint256)", "transfer(address,uint256)"]
# sha256 of canonical_json(generate(0, 32, FNS)). Changing the distribution
# changes this value: bump DIST_VERSION and update it (the distribution is
# part of the adversary id).
GOLDEN_SEED0_N32 = "2a350b9f51a531554fcde18c0bc31559a2a663a4d90890b699755fe96e66b510"


class Seqgen(unittest.TestCase):
    def test_tx_functions_of_b(self):
        self.assertEqual(seqgen.tx_functions(core.compile_artifact(TOKEN)), FNS)

    def test_same_seed_same_list(self):
        a = seqgen.generate(7, 64, FNS)
        b = seqgen.generate(7, 64, FNS)
        self.assertEqual(core.canonical_json(a), core.canonical_json(b))
        self.assertNotEqual(core.canonical_json(a), core.canonical_json(seqgen.generate(8, 64, FNS)))

    def test_sigma_depends_only_on_seed_and_index(self):
        full = seqgen.generate(3, 40, FNS)
        for i in (0, 17, 39):
            self.assertEqual(seqgen.gen_sigma(3, i, FNS), full[i])

    def test_golden_distribution(self):
        self.assertEqual(core.json_sha256(seqgen.generate(0, 32, FNS)), GOLDEN_SEED0_N32)

    def test_every_sigma_is_valid(self):
        for i, s in enumerate(seqgen.generate(11, 400, FNS)):
            core.validate_sigma(s)
            self.assertNotIn("probe", s)
            self.assertLessEqual(len(s["txs"]), seqgen.DEFAULT_MAX_TXS, i)

    def test_probe_appends_without_changing_the_prefix(self):
        checks = ["check_b", "check_a"]
        for i in range(100):
            with_probe = seqgen.gen_sigma(5, i, FNS, probe_checks=checks)
            core.validate_sigma(with_probe, need_probe=True)
            self.assertIn(with_probe["probe"]["check"], checks)
            bare = dict(with_probe)
            del bare["probe"]
            self.assertEqual(bare, seqgen.gen_sigma(5, i, FNS))

    def test_boundaries_are_drawn(self):
        sigmas = seqgen.generate(1, 600, FNS)
        caps = {int(s["ctor"]["cap"]) for s in sigmas}
        self.assertTrue({0, 1, 2, 2**255, core.UINT256_MAX - 1, core.UINT256_MAX} <= caps)
        rel = set()  # uint arguments relative to their sigma's cap
        for s in sigmas:
            cap = int(s["ctor"]["cap"])
            for tx in s["txs"]:
                v = int(tx["args"][1])
                for name, target in (("0", 0), ("max", core.UINT256_MAX), ("cap", cap),
                                     ("cap-1", cap - 1), ("cap+1", cap + 1)):
                    if v == target:
                        rel.add(name)
        self.assertEqual(rel, {"0", "max", "cap", "cap-1", "cap+1"})
        self.assertEqual({s["deployer"] for s in sigmas}, set(core.SENDERS))
        self.assertEqual({tx["args"][0] for s in sigmas for tx in s["txs"]}, set(core.POOL))
        self.assertEqual({len(s["txs"]) for s in sigmas}, set(range(seqgen.DEFAULT_MAX_TXS + 1)))

    def test_stream_below(self):
        st = seqgen.Stream(0, 0)
        self.assertEqual({st.below(1) for _ in range(20)}, {0})
        draws = [st.below(3) for _ in range(300)]
        self.assertEqual(set(draws), {0, 1, 2})
        with self.assertRaises(ValueError):
            st.below(0)

    def test_distribution_id(self):
        d = seqgen.distribution_id(FNS)
        self.assertEqual(d["dist_version"], seqgen.DIST_VERSION)
        self.assertEqual(d["fns"], FNS)
        self.assertEqual(d["source_sha256"], core.sha256_file(seqgen.__file__))


if __name__ == "__main__":
    unittest.main()
