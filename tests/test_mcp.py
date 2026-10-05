"""Tests for the MCP server: starts it for real and calls the tools."""
import json
import unittest

import core


class TestMCPServer(unittest.IsolatedAsyncioTestCase):
    async def test_lists_the_three_tools(self):
        async with core.mcp_session() as session:
            names = {t["name"] for t in await core.get_mcp_tools(session)}
        self.assertEqual(names, {"list_menu", "search_pizzas", "get_price"})

    async def test_get_price(self):
        async with core.mcp_session() as session:
            result = await session.call_tool("get_price", {"pizza": "Four Cheese", "size": "l"})
        self.assertEqual(json.loads(result.content[0].text)["price"], 58)

    async def test_unknown_pizza_is_an_error_with_hint(self):
        async with core.mcp_session() as session:
            result = await session.call_tool("get_price", {"pizza": "sushi"})
        self.assertTrue(result.isError)
        self.assertIn("Hint", result.content[0].text)



class TestMCPOutputFormats(unittest.IsolatedAsyncioTestCase):
    async def get_price_text(self, fmt):
        async with core.mcp_session(fmt) as session:
            result = await session.call_tool("get_price", {"pizza": "Margherita", "size": "L"})
        return result.content[0].text

    async def test_pretty_is_indented_json(self):
        text = await self.get_price_text("pretty")
        self.assertIn("\n", text)
        self.assertEqual(json.loads(text)["price"], 52)

    async def test_compact_is_one_line_json(self):
        text = await self.get_price_text("compact")
        self.assertNotIn("\n", text)
        self.assertEqual(json.loads(text)["price"], 52)

    async def test_text_is_plain(self):
        self.assertEqual(await self.get_price_text("text"), "Margherita (L): $52.00")


if __name__ == "__main__":
    unittest.main()
