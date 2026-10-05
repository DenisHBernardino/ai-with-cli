"""Tests for the shared logic (no API key needed)."""
import unittest

import core


class TestSafety(unittest.TestCase):
    def test_blocks_commands_outside_the_allowlist(self):
        self.assertIn("not allowed", core.run_cli("rm -rf /"))
        self.assertIn("not allowed", core.run_cli("cat data.json"))

    def test_no_shell_injection(self):
        # ';' is just text for the CLI, not a second command
        output = core.run_cli("price margherita; echo hacked")
        self.assertNotIn("hacked\n", output)
        self.assertIn("not found", output)

    def test_accepts_pizza_prefix(self):
        self.assertIn("$52.00", core.run_cli("pizza price margherita --size L"))


class TestScoring(unittest.TestCase):
    def test_is_correct_needs_all_words(self):
        self.assertTrue(core.is_correct("Nona Special and Four Cheese", ["four cheese", "nona special"]))
        self.assertFalse(core.is_correct("Only Four Cheese", ["four cheese", "nona special"]))

    def test_expected_for_test_questions(self):
        self.assertEqual(core.expected_for("How much is a large Margherita?"), ["52"])
        self.assertIsNone(core.expected_for("Do you sell sushi?"))


class TestFakeTools(unittest.TestCase):
    def test_enough_fake_tools_for_the_slider(self):
        self.assertGreaterEqual(len(core.FAKE_TOOL_NAMES), max(core.COST_STEPS) - 3)

    def test_fake_tool_names_are_unique(self):
        names = [t["name"] for t in core.fake_tools(47)]
        self.assertEqual(len(names), len(set(names)))


if __name__ == "__main__":
    unittest.main()
