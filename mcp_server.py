#!/usr/bin/env python3
"""
🔌 Nona Byte Pizza MCP server.

Same data as the CLI, different way to deliver it:
  - CLI: the AI types commands and reads text.
  - MCP: the AI gets a list of tools with a "form" (JSON schema)
         and fills in the fields.

Read-only. No tool changes any data.

The output format comes from the MCP_OUTPUT_FORMAT variable:
  pretty (default), compact or text. See formats.py.

Run it alone to test:  python mcp_server.py
(It waits for an MCP client, like experiment.py.)
"""
import os
from typing import Optional

from mcp.server.fastmcp import FastMCP

from formats import FORMATS, render
# Reuse the CLI functions: one single source of truth
from pizza import find_pizza, load_pizzas, normalize

OUTPUT_FORMAT = os.getenv("MCP_OUTPUT_FORMAT", "pretty")
if OUTPUT_FORMAT not in FORMATS:
    raise SystemExit(f"MCP_OUTPUT_FORMAT must be one of: {', '.join(FORMATS)}")

mcp = FastMCP("nona-byte-pizza", log_level="WARNING")  # fewer logs in the terminal


@mcp.tool()
def list_menu(vegetarian: bool = False, available: bool = False) -> str:
    """List the pizzas with ingredients, prices (S, M, L), if vegetarian and if available today."""
    pizzas = load_pizzas()
    if vegetarian:
        pizzas = [p for p in pizzas if p["vegetarian"]]
    if available:
        pizzas = [p for p in pizzas if p["available"]]
    return render(pizzas, OUTPUT_FORMAT)


@mcp.tool()
def search_pizzas(terms: list[str]) -> str:
    """Find pizzas that have ALL the terms in the name or ingredients. E.g. ["mushroom", "bell pepper"]."""
    targets = [normalize(t) for t in terms]

    def matches(p):
        fields = [normalize(p["name"])] + [normalize(i) for i in p["ingredients"]]
        return all(any(t in f for f in fields) for t in targets)

    return render([p for p in load_pizzas() if matches(p)], OUTPUT_FORMAT)


@mcp.tool()
def get_price(pizza: str, size: Optional[str] = None) -> str:
    """Price of a pizza by name. Size: S, M or L. Without size, returns all three."""
    p = find_pizza(load_pizzas(), pizza)
    if not p:
        # Error with a hint: the AI uses this to fix itself
        raise ValueError(f"Pizza '{pizza}' not found. Hint: use list_menu to see the names.")

    if size:
        size = size.upper()
        if size not in p["prices"]:
            raise ValueError("Invalid size. Use S, M or L.")
        data = {"pizza": p["name"], "size": size, "price": p["prices"][size], "available": p["available"]}
    else:
        data = {"pizza": p["name"], "prices": p["prices"], "available": p["available"]}
    return render(data, OUTPUT_FORMAT)


if __name__ == "__main__":
    mcp.run()  # talks over stdin/stdout ("stdio" transport)
