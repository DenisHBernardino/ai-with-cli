"""
🧠 Shared logic for experiment.py and app.py.

Everything that talks to the AI lives here:
  - the CLI tool and the safe way to run it
  - the MCP connection
  - the "ask" loop (AI asks for a tool -> we run it -> AI answers)
  - scoring and token counting
"""
import json
import os
import shlex
import subprocess
import sys
import time
import unicodedata
from contextlib import asynccontextmanager
from pathlib import Path

import anthropic
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Reads the .env file (if it exists) into environment variables.
# A variable already set in the terminal wins over the .env file.
load_dotenv(Path(__file__).parent / ".env")

MODEL = os.getenv("MODEL", "claude-sonnet-5-5")
FOLDER = Path(__file__).parent
SYSTEM = "You work at Nona Byte Pizza. Answer in English, short and direct. Plain text only, no Markdown."
MODES = ["none", "cli", "mcp"]

_client = None


def has_api_key():
    key = os.getenv("ANTHROPIC_API_KEY", "")
    return bool(key) and "your-key" not in key  # ignore the placeholder from .env.example


def get_client():
    """Create the API client only when needed (so replay mode works without a key)."""
    global _client
    if _client is None:
        _client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY
    return _client


def load_questions():
    return json.loads((FOLDER / "questions.json").read_text(encoding="utf-8"))


# ================= CLI =================

# For the CLI, we give ONE tool: "a terminal that only runs 'pizza'".
# Careful: the AI copies the examples in a tool description. An earlier version
# showed 'menu --json' here, and the AI asked for JSON almost every time.
CLI_TOOL = {
    "name": "pizza",
    "description": (
        "Runs the Nona Byte Pizza CLI. Pass the arguments as you would type "
        "them in a terminal after 'pizza'. If you don't know the commands, "
        "start with '--help'. Examples: '--help', 'menu', 'price margherita --size L'."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "args": {"type": "string", "description": "e.g. 'price margherita --size L'"}
        },
        "required": ["args"],
    },
}

# Safety: the AI can only run these commands (all read-only).
ALLOWED_COMMANDS = {"--help", "-h", "menu", "search", "price"}


def run_cli(args):
    try:
        parts = shlex.split(args)
    except ValueError:
        return "Error: invalid arguments (open quotes?)."
    if parts and parts[0] == "pizza":
        parts = parts[1:]
    if not parts or parts[0] not in ALLOWED_COMMANDS:
        return f"Error: command not allowed. Use one of these: {sorted(ALLOWED_COMMANDS)}"

    # A list of arguments, never a shell string: the AI can't inject commands.
    result = subprocess.run(
        [sys.executable, str(FOLDER / "pizza.py"), *parts],
        capture_output=True, text=True, encoding="utf-8", timeout=10,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    return (result.stdout + result.stderr).strip() or "(no output)"


# ================= MCP =================

@asynccontextmanager
async def mcp_session(fmt="pretty"):
    """
    Start the MCP server as a child process and connect to it.
    fmt = output format of the tools: "pretty", "compact" or "text" (see formats.py).
    """
    server = StdioServerParameters(
        command=sys.executable,
        args=[str(FOLDER / "mcp_server.py")],
        env={**os.environ, "MCP_OUTPUT_FORMAT": fmt, "PYTHONIOENCODING": "utf-8"},
    )
    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


async def get_mcp_tools(session):
    """Ask the MCP server which tools it has and convert them to the API format."""
    response = await session.list_tools()
    return [
        {"name": t.name, "description": t.description or "", "input_schema": t.inputSchema}
        for t in response.tools
    ]


# ================= counting tokens of a text =================

_token_cache = {}


def count_text_tokens(text, model=None):
    """
    How many tokens a piece of text costs for the model (real count from the API).
    We count a message with the text and remove the small fixed cost of any message.
    """
    model = model or MODEL
    if (model, text) in _token_cache:
        return _token_cache[(model, text)]

    def count(t):
        return get_client().messages.count_tokens(
            model=model, messages=[{"role": "user", "content": t}]
        ).input_tokens

    if (model, None) not in _token_cache:
        _token_cache[(model, None)] = count("a") - 1  # fixed cost of a message
    n = count(text) - _token_cache[(model, None)]
    _token_cache[(model, text)] = n
    return n


# ================= the ask loop =================

async def ask(question, mode, session=None, mcp_tools=None, model=None, measure=True):
    """
    Ask one question in one mode: "none", "cli" or "mcp".
    Returns the answer, a trace of every tool the AI used, and the tokens split by type:
      - input_tokens:       everything the AI read (question, tool menu, tool outputs, history)
      - output_tokens:      everything the AI wrote (its answer and its tool calls)
      - tool_output_tokens: only the tool outputs, counted once each
    """
    model = model or MODEL
    if mode == "cli":
        tools = [CLI_TOOL]
    elif mode == "mcp":
        tools = mcp_tools
    else:
        tools = []

    messages = [{"role": "user", "content": question}]
    extra = {"tools": tools} if tools else {}
    trace, start = [], time.time()
    input_tokens = output_tokens = 0

    for _ in range(10):  # max rounds, so it never loops forever
        response = get_client().messages.create(
            model=model, max_tokens=1024, system=SYSTEM, messages=messages, **extra
        )
        input_tokens += response.usage.input_tokens
        output_tokens += response.usage.output_tokens

        if response.stop_reason != "tool_use":
            answer = "".join(b.text for b in response.content if b.type == "text").strip()
            break

        messages.append({"role": "assistant", "content": response.content})
        results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            if mode == "cli":
                args = block.input.get("args", "")
                label = f"pizza {args}"
                output = run_cli(args)
            else:
                label = f"{block.name}({json.dumps(block.input, ensure_ascii=False)})"
                result = await session.call_tool(block.name, block.input)
                output = "".join(c.text for c in result.content if c.type == "text") or "(no output)"
            step = {"call": label, "output": output, "tokens": None}
            if measure:
                try:
                    step["tokens"] = count_text_tokens(output, model)
                except Exception:
                    pass  # counting is a bonus: never break the answer because of it
            trace.append(step)
            results.append({"type": "tool_result", "tool_use_id": block.id, "content": output})
        messages.append({"role": "user", "content": results})
    else:
        answer = "(gave up: too many calls)"

    counted = [s["tokens"] for s in trace]
    return {
        "answer": answer,
        "tokens": input_tokens + output_tokens,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "tool_output_tokens": None if None in counted else sum(counted),
        "calls": len(trace),
        "seconds": round(time.time() - start, 1),
        "trace": trace,
    }


async def ask_once(question, mode, fmt="pretty"):
    """Same as ask(), but opens its own MCP connection when needed (used by the web app)."""
    if mode != "mcp":
        return await ask(question, mode)
    async with mcp_session(fmt) as session:
        tools = await get_mcp_tools(session)
        return await ask(question, mode, session, tools)


# ================= scoring =================

def normalize(text):
    text = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in text if not unicodedata.combining(c))


def is_correct(answer, expected):
    """Correct if ALL expected words appear in the answer."""
    a = normalize(answer)
    return all(normalize(e) in a for e in expected)


def expected_for(question):
    """The expected answer, if this is one of the test questions."""
    for item in load_questions():
        if normalize(item["question"]).strip() == normalize(question).strip():
            return item["expected"]
    return None


# ================= the hidden cost =================

# Fake tools: a big pizza-shop MCP server could have all of these.
# They are ONLY counted, never run.
FAKE_TOOL_NAMES = [
    ("track_delivery", "Track where a delivery driver is right now."),
    ("apply_coupon", "Apply a discount coupon to an order."),
    ("get_loyalty_points", "Get the loyalty points of a customer."),
    ("list_stores", "List all store locations with address."),
    ("get_store_hours", "Get opening hours of a store."),
    ("get_delivery_fee", "Calculate the delivery fee for an address."),
    ("estimate_delivery_time", "Estimate how long a delivery will take."),
    ("create_order", "Create a new order."),
    ("cancel_order", "Cancel an existing order."),
    ("update_order", "Change items in an existing order."),
    ("get_order_status", "Get the status of an order."),
    ("list_orders", "List the orders of a customer."),
    ("get_customer", "Get a customer profile."),
    ("update_customer", "Update a customer profile."),
    ("list_drinks", "List drinks and their prices."),
    ("list_desserts", "List desserts and their prices."),
    ("list_combos", "List combo deals."),
    ("get_combo_price", "Get the price of a combo deal."),
    ("check_allergens", "Check allergens in a pizza."),
    ("get_nutrition", "Get nutrition facts of a pizza."),
    ("list_toppings", "List extra toppings and prices."),
    ("add_topping", "Add an extra topping to a pizza in an order."),
    ("rate_order", "Rate an order from 1 to 5."),
    ("list_reviews", "List customer reviews."),
    ("reply_review", "Reply to a customer review."),
    ("get_inventory", "Get stock levels of ingredients."),
    ("reorder_ingredient", "Order more of an ingredient from a supplier."),
    ("list_suppliers", "List ingredient suppliers."),
    ("list_employees", "List employees of a store."),
    ("get_schedule", "Get the work schedule of an employee."),
    ("clock_in", "Register an employee clock-in."),
    ("clock_out", "Register an employee clock-out."),
    ("get_daily_sales", "Get total sales for a day."),
    ("get_top_pizzas", "Get the best-selling pizzas."),
    ("refund_order", "Refund an order."),
    ("send_receipt", "Send a receipt by email."),
    ("list_payment_methods", "List accepted payment methods."),
    ("validate_address", "Check if an address is in the delivery area."),
    ("list_delivery_zones", "List delivery zones and fees."),
    ("assign_driver", "Assign a driver to a delivery."),
    ("list_drivers", "List available drivers."),
    ("get_weather", "Get the weather that may delay deliveries."),
    ("list_promotions", "List active promotions."),
    ("create_promotion", "Create a new promotion."),
    ("subscribe_newsletter", "Subscribe a customer to the newsletter."),
    ("book_table", "Book a table at a store."),
    ("list_bookings", "List table bookings for a day."),
]

FAKE_PARAMS = [
    {"order_id": {"type": "string", "description": "Order ID, e.g. 'A-1001'"}},
    {"customer_id": {"type": "string", "description": "Customer ID"},
     "store_id": {"type": "string", "description": "Store ID"}},
    {"date": {"type": "string", "description": "Date in YYYY-MM-DD format"},
     "limit": {"type": "integer", "description": "Max number of results"}},
]


def fake_tools(n):
    """Build n fake tools that look like real MCP tools."""
    tools = []
    for i, (name, description) in enumerate(FAKE_TOOL_NAMES[:n]):
        params = FAKE_PARAMS[i % len(FAKE_PARAMS)]
        tools.append({
            "name": name,
            "description": description,
            "input_schema": {"type": "object", "properties": params, "required": [next(iter(params))]},
        })
    return tools


def fixed_cost(tools):
    """How many tokens the tool DESCRIPTIONS add to every call (real count from the API)."""
    if not tools:
        return 0
    base = [{"role": "user", "content": "hi"}]
    client = get_client()
    without = client.messages.count_tokens(model=MODEL, system=SYSTEM, messages=base).input_tokens
    with_tools = client.messages.count_tokens(
        model=MODEL, system=SYSTEM, messages=base, tools=tools
    ).input_tokens
    return with_tools - without


# Slider steps: how many MCP tools
COST_STEPS = [3, 5, 10, 20, 30, 40, 50]


async def all_costs():
    """Fixed cost of the CLI and of MCP with 3 to 50 tools."""
    async with mcp_session() as session:
        real = await get_mcp_tools(session)
    mcp = {n: fixed_cost(real + fake_tools(n - len(real))) for n in COST_STEPS}
    return {"cli": fixed_cost([CLI_TOOL]), "mcp": mcp}


# ================= the output format lab =================

# The same 5 tool calls, used to compare output formats.
LAB_CALLS = [
    ("list_menu", {}),
    ("list_menu", {"vegetarian": True}),
    ("list_menu", {"available": True}),
    ("search_pizzas", {"terms": ["mushroom"]}),
    ("get_price", {"pizza": "Margherita", "size": "L"}),
]


def call_label(name, args):
    inside = ", ".join(f"{k}={json.dumps(v, ensure_ascii=False)}" for k, v in args.items())
    return f"{name}({inside})"


async def format_lab(model=None):
    """
    Same calls, same MCP server, same data. Only the output format changes.
    No AI answer is generated: we only count the tokens of each tool output.
    So the format is the ONLY variable.
    """
    from formats import FORMATS
    rows = [{"call": call_label(n, a), "tokens": {}, "lines": {}} for n, a in LAB_CALLS]
    for fmt in FORMATS:
        async with mcp_session(fmt) as session:
            for row, (name, args) in zip(rows, LAB_CALLS):
                result = await session.call_tool(name, args)
                text = "".join(c.text for c in result.content if c.type == "text")
                row["tokens"][fmt] = count_text_tokens(text, model)
                row["lines"][fmt] = text.count("\n") + 1
    totals = {fmt: sum(r["tokens"][fmt] for r in rows) for fmt in FORMATS}
    return {"model": model or MODEL, "calls": rows, "totals": totals}
