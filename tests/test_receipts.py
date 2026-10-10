import copy
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "verify_receipts", ROOT / "scripts" / "verify_receipts.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ReceiptVerificationTests(unittest.TestCase):
    def setUp(self):
        self.sender = json.loads((ROOT / "examples/sender-result.json").read_text())
        self.target = json.loads((ROOT / "examples/target-receipt.json").read_text())

    def test_exact_completed_pair(self):
        result = MODULE.verify(self.sender, self.target)
        self.assertTrue(result["verified"])
        self.assertTrue(result["synthetic"])
        self.assertFalse(result["origin_authenticated_by_this_comparison"])

    def test_accepted_but_incomplete_is_not_success(self):
        self.sender["control"]["turn_completed"] = False
        with self.assertRaises(ValueError):
            MODULE.verify(self.sender, self.target)

    def test_wrong_thread_or_turn_is_rejected(self):
        for kind in ("thread", "turn"):
            target = copy.deepcopy(self.target)
            if kind == "thread":
                target["thread"]["id"] = "different-thread"
            else:
                target["turns"][0]["id"] = "different-turn"
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                MODULE.verify(self.sender, target)

    def test_substring_nonce_is_not_exact_reply(self):
        self.target["turns"][0]["items"][0]["text"] = "Some text " + self.sender["control"]["nonce"]
        with self.assertRaises(ValueError):
            MODULE.verify(self.sender, self.target)

    def test_failed_or_duplicate_target_turn_is_rejected(self):
        failed = copy.deepcopy(self.target)
        failed["turns"][0]["error"] = {"message": "failed"}
        with self.assertRaises(ValueError):
            MODULE.verify(self.sender, failed)
        duplicate = copy.deepcopy(self.target)
        duplicate["turns"].append(copy.deepcopy(duplicate["turns"][0]))
        with self.assertRaises(ValueError):
            MODULE.verify(self.sender, duplicate)


if __name__ == "__main__":
    unittest.main()
