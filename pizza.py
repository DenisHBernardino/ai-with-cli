#!/usr/bin/env python3
"""
🍕 Nona Byte Pizza: a sample CLI.

This is the CLI the AI will use.
It only READS data (data.json). It never changes anything.

Three things make a CLI "AI-friendly":
  1. Clear --help with examples -> the AI learns how to use it on its own
  2. --json                     -> the AI reads the output without mistakes
  3. Helpful error messages     -> the AI fixes its own command
"""
import argparse
import json
import sys
import unicodedata
from pathlib import Path

DATA_FILE = Path(__file__).parent / "data.json"

# Make emojis work in any terminal (Windows too)
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except AttributeError:
    pass


# ---------- helpers ----------

def load_pizzas():
    with open(DATA_FILE, encoding="utf-8") as f:
        return json.load(f)["pizzas"]


def normalize(text):
    """'Ham & Egg' -> 'ham and egg'. Search ignores case, accents and '&'."""
    text = unicodedata.normalize("NFKD", text.lower().replace("&", " and "))
    text = "".join(c for c in text if not unicodedata.combining(c))
    return " ".join(text.split())


def money(value):
    return f"${value:.2f}"


def find_pizza(pizzas, name):
    target = normalize(name)
    for p in pizzas:
        if normalize(p["name"]) == target or p["id"] == target:
            return p
    return None


def error(message):
    """Clear error + a hint. The AI uses this to fix itself."""
    print(f"Error: {message}", file=sys.stderr)
    sys.exit(1)


def show(data, as_json, text):
    if as_json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(text)


def format_pizza(p):
    prices = " | ".join(f"{s} {money(v)}" for s, v in p["prices"].items())
    tags = []
    if p["vegetarian"]:
        tags.append("🌱 vegetarian")
    if not p["available"]:
        tags.append("❌ sold out today")
    extra = f"  ({', '.join(tags)})" if tags else ""
    return f"🍕 {p['name']}: {prices}{extra}\n   {', '.join(p['ingredients'])}"


# ---------- commands ----------

def cmd_menu(args, pizzas):
    items = pizzas
    if args.vegetarian:
        items = [p for p in items if p["vegetarian"]]
    if args.available:
        items = [p for p in items if p["available"]]
    text = "\n".join(format_pizza(p) for p in items) or "No pizzas found."
    show(items, args.json, text)


def cmd_search(args, pizzas):
    terms = [normalize(t) for t in args.terms]

    def matches(p):
        fields = [normalize(p["name"])] + [normalize(i) for i in p["ingredients"]]
        # every term must appear (in the name or in the ingredients)
        return all(any(t in f for f in fields) for t in terms)

    found = [p for p in pizzas if matches(p)]
    text = "\n".join(format_pizza(p) for p in found) or "No pizzas found."
    show(found, args.json, text)


def cmd_price(args, pizzas):
    name = " ".join(args.pizza)
    p = find_pizza(pizzas, name)
    if not p:
        error(f"pizza '{name}' not found. Hint: run 'menu' to see the names.")

    if args.size:
        value = p["prices"][args.size]
        data = {"pizza": p["name"], "size": args.size, "price": value, "available": p["available"]}
        text = f"{p['name']} ({args.size}): {money(value)}"
    else:
        data = {"pizza": p["name"], "prices": p["prices"], "available": p["available"]}
        text = f"{p['name']}: " + " | ".join(f"{s} {money(v)}" for s, v in p["prices"].items())

    if not p["available"]:
        text += "  ⚠️ sold out today"
    show(data, args.json, text)


# ---------- CLI setup ----------

def main():
    # option that every command accepts
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--json", action="store_true", help="JSON output (great for AI and scripts)")

    parser = argparse.ArgumentParser(
        prog="pizza",
        description="🍕 Nona Byte Pizza CLI. Check the menu, ingredients and prices.",
        epilog=(
            "Examples:\n"
            "  pizza menu\n"
            "  pizza menu --vegetarian\n"
            "  pizza search mushroom\n"
            "  pizza price margherita --size L\n"
            "  pizza price four cheese --json"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", metavar="COMMAND", required=True)

    m = sub.add_parser("menu", parents=[common], help="list the pizzas")
    m.add_argument("--vegetarian", action="store_true", help="only vegetarian pizzas")
    m.add_argument("--available", action="store_true", help="only pizzas available today")
    m.set_defaults(func=cmd_menu)

    s = sub.add_parser("search", parents=[common], help="search by name or ingredient")
    s.add_argument("terms", nargs="+", help="one or more terms (e.g. mushroom bell pepper)")
    s.set_defaults(func=cmd_search)

    p = sub.add_parser("price", parents=[common], help="show the price of a pizza")
    p.add_argument("pizza", nargs="+", help="pizza name (e.g. four cheese)")
    p.add_argument("--size", type=str.upper, choices=["S", "M", "L"],
                   help="S (small), M (medium) or L (large)")
    p.set_defaults(func=cmd_price)

    args = parser.parse_args()
    args.func(args, load_pizzas())


if __name__ == "__main__":
    main()
