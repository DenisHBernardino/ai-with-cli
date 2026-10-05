"""Tests for the pizza CLI. Run: python -m unittest discover -s tests -t . -v"""
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).parent.parent


def run(*args):
    return subprocess.run(
        [sys.executable, str(ROOT / "pizza.py"), *args],
        capture_output=True, text=True, encoding="utf-8",
    )


class TestPizzaCLI(unittest.TestCase):
    def test_help_has_examples(self):
        result = run("--help")
        self.assertEqual(result.returncode, 0)
        self.assertIn("Examples:", result.stdout)

    def test_menu_json_lists_all_pizzas(self):
        pizzas = json.loads(run("menu", "--json").stdout)
        self.assertEqual(len(pizzas), 7)

    def test_vegetarian_filter(self):
        names = {p["name"] for p in json.loads(run("menu", "--vegetarian", "--json").stdout)}
        self.assertEqual(names, {"Margherita", "Four Cheese", "Nona Special", "Banana Cinnamon"})

    def test_price_with_size(self):
        data = json.loads(run("price", "margherita", "--size", "L", "--json").stdout)
        self.assertEqual(data["price"], 52)

    def test_price_name_with_spaces_and_ampersand(self):
        self.assertIn("$45.00", run("price", "ham", "and", "egg", "--size", "m").stdout)
        self.assertIn("$45.00", run("price", "Ham & Egg", "--size", "M").stdout)

    def test_search_needs_all_terms(self):
        found = json.loads(run("search", "mushroom", "bell pepper", "--json").stdout)
        self.assertEqual([p["name"] for p in found], ["Nona Special"])

    def test_sold_out_warning(self):
        self.assertIn("sold out", run("price", "pepperoni").stdout)

    def test_unknown_pizza_gives_hint(self):
        result = run("price", "sushi")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Hint", result.stderr)


if __name__ == "__main__":
    unittest.main()
