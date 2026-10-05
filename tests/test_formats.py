"""Tests for the output formats: same data, different shape."""
import json
import unittest

from formats import FORMATS, render
from pizza import load_pizzas


class TestFormats(unittest.TestCase):
    def setUp(self):
        self.menu = load_pizzas()
        self.price = {"pizza": "Margherita", "size": "L", "price": 52, "available": True}

    def test_json_formats_keep_the_same_data(self):
        for data in (self.menu, self.price):
            self.assertEqual(json.loads(render(data, "pretty")), json.loads(render(data, "compact")))

    def test_compact_is_shorter_than_pretty(self):
        self.assertLess(len(render(self.menu, "compact")), len(render(self.menu, "pretty")))

    def test_text_has_no_json(self):
        text = render(self.menu, "text")
        self.assertNotIn("{", text)
        self.assertIn("Nona Special", text)

    def test_text_price_matches_the_cli(self):
        self.assertEqual(render(self.price, "text"), "Margherita (L): $52.00")

    def test_text_shows_sold_out(self):
        pepperoni = {"pizza": "Pepperoni", "size": "S", "price": 30, "available": False}
        self.assertIn("sold out", render(pepperoni, "text"))

    def test_unknown_format_fails(self):
        with self.assertRaises(ValueError):
            render(self.price, "xml")

    def test_all_formats_listed(self):
        self.assertEqual(FORMATS, ["pretty", "compact", "text"])


if __name__ == "__main__":
    unittest.main()
