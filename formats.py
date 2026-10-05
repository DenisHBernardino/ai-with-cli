"""
📦 Output formats for the MCP tools.

Same data, three ways to send it back to the AI:
  - pretty:  JSON with line breaks and indentation (easy for humans to read)
  - compact: JSON with no spaces (same data, fewer characters)
  - text:    short plain text, exactly what the CLI prints

The format is the ONLY thing that changes. The data is always the same.
"""
import json

from pizza import format_pizza, price_text

FORMATS = ["pretty", "compact", "text"]
LABELS = {"pretty": "Pretty JSON", "compact": "Compact JSON", "text": "Plain text"}


def render(data, fmt):
    if fmt == "pretty":
        return json.dumps(data, ensure_ascii=False, indent=2)
    if fmt == "compact":
        return json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    if fmt == "text":
        if isinstance(data, list):
            return "\n".join(format_pizza(p) for p in data) or "No pizzas found."
        return price_text(data)
    raise ValueError(f"Unknown format '{fmt}'. Use one of: {', '.join(FORMATS)}")
