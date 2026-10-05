#!/usr/bin/env python3
"""
🔌 Nona Byte Pizza MCP server.

Same data as the CLI, different way to deliver it:
  - CLI: the AI types commands and reads text.
  - MCP: the AI gets a list of tools with a "form" (JSON schema)
         and fills in the fields.

Read-only. No tool changes any data.
Run it alone to test:  python mcp_server.py
(It waits for an MCP client, like experiment.py.)
"""
from typing import Optional

from mcp.server.fastmcp import FastMCP

# Reuse the CLI functions: one single source of truth
from pizza import find_pizza, load_pizzas, normalize

mcp = FastMCP("nona-byte-pizza", log_level="WARNING")  # fewer logs in the terminal


@mcp.tool()
def list_menu(vegetarian: bool = False, available: bool = False) -> list:
    """List the pizzas with ingredients, prices (S, M, L), if vegetarian and if available today."""
    pizzas = load_pizzas()
    if vegetarian:
        pizzas = [p for p in pizzas if p["vegetarian"]]
    if available:
        pizzas = [p for p in pizzas if p["available"]]
    return pizzas


@mcp.tool()
def search_pizzas(terms: list[str]) -> list:
    """Find pizzas that have ALL the terms in the name or ingredients. E.g. ["mushroom", "bell pepper"]."""
    targets = [normalize(t) for t in terms]

    def matches(p):
        fields = [normalize(p["name"])] + [normalize(i) for i in p["ingredients"]]
        return all(any(t in f for f in fields) for t in targets)

    return [p for p in load_pizzas() if matches(p)]


@mcp.tool()
def get_price(pizza: str, size: Optional[str] = None) -> dict:
    """Price of a pizza by name. Size: S, M or L. Without size, returns all three."""
    p = find_pizza(load_pizzas(), pizza)
    if not p:
        # Error with a hint: the AI uses this to fix itself
        raise ValueError(f"Pizza '{pizza}' not found. Hint: use list_menu to see the names.")

    if size:
        size = size.upper()
        if size not in p["prices"]:
            raise ValueError("Invalid size. Use S, M or L.")
        return {"pizza": p["name"], "size": size, "price": p["prices"][size], "available": p["available"]}

    return {"pizza": p["name"], "prices": p["prices"], "available": p["available"]}


if __name__ == "__main__":
    mcp.run()  # talks over stdin/stdout ("stdio" transport)
