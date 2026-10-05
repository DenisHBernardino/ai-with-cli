#!/usr/bin/env python3
"""
🧪 Experiment: how does the AI answer in 3 scenarios?

Asks the same questions three times:
  A) NO tools  -> the AI only has what it "remembers"
  B) WITH CLI  -> the AI can run the 'pizza' command in a terminal
  C) WITH MCP  -> the AI gets the tools from the MCP server

At the end, it shows correct answers, tokens and the "fixed cost" of each mode.
"""
import asyncio
import json
import os
import shlex
import subprocess
import sys
import unicodedata
from pathlib import Path

import anthropic
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

MODEL = os.getenv("MODEL", "claude-sonnet-5-5")
FOLDER = Path(__file__).parent
client = anthropic.Anthropic()  # reads the key from ANTHROPIC_API_KEY

SYSTEM = "You work at Nona Byte Pizza. Answer in English, short and direct."


# ================= CLI =================

# For the CLI, we give ONE tool: "a terminal that only runs 'pizza'".
CLI_TOOL = {
    "name": "pizza",
    "description": (
        "Runs the Nona Byte Pizza CLI. Pass the arguments as you would type "
        "them in a terminal after 'pizza'. If you don't know the commands, "
        "start with '--help'. Examples: '--help', 'menu --json'."
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

    result = subprocess.run(
        [sys.executable, str(FOLDER / "pizza.py"), *parts],
        capture_output=True, text=True, encoding="utf-8", timeout=10,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    return (result.stdout + result.stderr).strip() or "(no output)"


async def execute_cli(name, tool_input):
    args = tool_input.get("args", "")
    print(f"     🔧 AI ran: pizza {args}")
    return run_cli(args)


# ================= MCP =================

async def get_mcp_tools(session):
    """Ask the MCP server which tools it has and convert them to the API format."""
    response = await session.list_tools()
    return [
        {"name": t.name, "description": t.description or "", "input_schema": t.inputSchema}
        for t in response.tools
    ]


def make_mcp_executor(session):
    async def execute_mcp(name, tool_input):
        print(f"     🔌 AI called: {name}({json.dumps(tool_input, ensure_ascii=False)})")
        result = await session.call_tool(name, tool_input)
        text = "".join(c.text for c in result.content if c.type == "text")
        return text or "(no output)"
    return execute_mcp


# ================= talking to the AI =================

async def ask(question, tools, execute):
    """Talk to the AI. If it asks for a tool, we run it and send back the result."""
    messages = [{"role": "user", "content": question}]
    extra = {"tools": tools} if tools else {}
    tokens = 0
    calls = 0

    for _ in range(10):  # max rounds, so it never loops forever
        response = client.messages.create(
            model=MODEL, max_tokens=1024, system=SYSTEM, messages=messages, **extra
        )
        tokens += response.usage.input_tokens + response.usage.output_tokens

        if response.stop_reason != "tool_use":
            text = "".join(b.text for b in response.content if b.type == "text")
            return text.strip(), tokens, calls

        messages.append({"role": "assistant", "content": response.content})
        results = []
        for block in response.content:
            if block.type == "tool_use":
                calls += 1
                output = await execute(block.name, block.input)
                results.append({"type": "tool_result", "tool_use_id": block.id, "content": output})
        messages.append({"role": "user", "content": results})

    return "(gave up: too many calls)", tokens, calls


def fixed_cost(tools):
    """How many tokens the tool DESCRIPTIONS cost on every call."""
    base = [{"role": "user", "content": "hi"}]
    try:
        if not tools:
            return 0
        without = client.messages.count_tokens(model=MODEL, system=SYSTEM, messages=base).input_tokens
        with_tools = client.messages.count_tokens(
            model=MODEL, system=SYSTEM, messages=base, tools=tools
        ).input_tokens
        return with_tools - without
    except Exception:
        return None  # if counting fails, the experiment keeps going


# ================= scoreboard =================

def normalize(text):
    text = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in text if not unicodedata.combining(c))


def is_correct(answer, expected):
    """Correct if ALL expected words appear in the answer."""
    a = normalize(answer)
    return all(normalize(e) in a for e in expected)


def number(n):
    return "?" if n is None else f"{n:,}"


async def main():
    questions = json.loads((FOLDER / "questions.json").read_text(encoding="utf-8"))

    # Start the MCP server (it runs as a child process)
    server = StdioServerParameters(command=sys.executable, args=[str(FOLDER / "mcp_server.py")])
    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            mcp_tools = await get_mcp_tools(session)

            modes = {
                "no tools": ([], None),
                "with CLI": ([CLI_TOOL], execute_cli),
                "with MCP": (mcp_tools, make_mcp_executor(session)),
            }
            score = {m: {"correct": 0, "tokens": 0, "calls": 0} for m in modes}

            for i, item in enumerate(questions, 1):
                print(f"\n❓ {i}. {item['question']}")
                for mode, (tools, execute) in modes.items():
                    answer, tokens, calls = await ask(item["question"], tools, execute)
                    ok = is_correct(answer, item["expected"])
                    score[mode]["correct"] += ok
                    score[mode]["tokens"] += tokens
                    score[mode]["calls"] += calls
                    summary = answer.replace("\n", " ")[:110]
                    print(f"  {'✅' if ok else '❌'} [{mode}] {summary}")

    total = len(questions)
    print("\n📊 Results (copy to the README):\n")
    print("| Mode | Correct | Total tokens | Tool calls | Fixed cost per call |")
    print("|---|---|---|---|---|")
    for mode, (tools, _) in modes.items():
        s = score[mode]
        print(f"| {mode} | {s['correct']}/{total} | {number(s['tokens'])} | {s['calls']} | {number(fixed_cost(tools))} tokens |")


if __name__ == "__main__":
    asyncio.run(main())
