#!/usr/bin/env python3
"""
📦 The output format lab: does the FORMAT of a tool's answer change the cost?

Part 1 (default): isolated test
  The same 5 MCP calls, the same server, the same data.
  Only the output format changes: pretty JSON, compact JSON or plain text.
  No AI answer is generated, we only count tokens. The format is the only variable.

Part 2 (--e2e): end-to-end test
  The 6 test questions, answered by the AI with MCP in each format (plus the CLI).
  Tokens are split: tool outputs, everything the AI read, everything the AI wrote.
  Results are shown per model, never averaged across models.

  python format_lab.py                         # part 1 (cheap: only token counting)
  python format_lab.py --e2e --runs 3          # part 1 + part 2
  python format_lab.py --e2e --models claude-sonnet-5-5 claude-haiku-4-5
  python format_lab.py --e2e --save            # also saves runs/format_lab.json
"""
import argparse
import asyncio
import json

import core
from formats import FORMATS, LABELS


def pct(value, base):
    return "0%" if value == base else f"{(value - base) / base * 100:+.0f}%"


def print_isolated(lab):
    print(f"\n📦 Part 1: isolated test (model: {lab['model']})")
    print("Same calls, same data. Only the format changes.\n")
    head = " | ".join(LABELS[f] for f in FORMATS)
    print(f"| Tool call | {head} |")
    print("|---|" + "---|" * len(FORMATS))
    for row in lab["calls"]:
        cells = " | ".join(
            f"{row['tokens'][f]:,} ({row['lines'][f]} line{'s' if row['lines'][f] > 1 else ''})" for f in FORMATS
        )
        print(f"| `{row['call']}` | {cells} |")
    base = lab["totals"]["pretty"]
    cells = " | ".join(f"**{lab['totals'][f]:,}** ({pct(lab['totals'][f], base)})" for f in FORMATS)
    print(f"| **Total** | {cells} |")


async def run_setup(model, mode, fmt, questions, runs):
    """Run all questions in one setup and return the averages per run."""
    total = {"correct": 0, "calls": 0, "tool_output": 0, "input": 0, "output": 0}

    async def go(session=None, tools=None):
        for item in questions:
            for _ in range(runs):
                r = await core.ask(item["question"], mode, session, tools, model=model)
                total["correct"] += core.is_correct(r["answer"], item["expected"])
                total["calls"] += r["calls"]
                total["tool_output"] += r["tool_output_tokens"] or 0
                total["input"] += r["input_tokens"]
                total["output"] += r["output_tokens"]
                print("✅" if core.is_correct(r["answer"], item["expected"]) else "❌", end="", flush=True)

    if mode == "mcp":
        async with core.mcp_session(fmt) as session:
            await go(session, await core.get_mcp_tools(session))
    else:
        await go()
    print()
    return {k: v / runs for k, v in total.items()}


async def run_e2e(models, runs):
    questions = core.load_questions()
    setups = [("CLI", "cli", None)] + [(f"MCP, {LABELS[f]}", "mcp", f) for f in FORMATS]
    results = {}
    for model in models:
        print(f"\n🧪 Part 2: end-to-end test (model: {model}, {runs} run(s) per question)")
        results[model] = {}
        for label, mode, fmt in setups:
            print(f"  {label}: ", end="")
            results[model][label] = await run_setup(model, mode, fmt, questions, runs)

        n = len(questions)
        base = results[model]["MCP, Pretty JSON"]
        print(f"\n| Setup | Correct | Tool calls | Tool output tokens | AI read | AI wrote | Total |")
        print("|---|---|---|---|---|---|---|")
        for label, r in results[model].items():
            total = r["input"] + r["output"]
            print(
                f"| {label} | {r['correct']:.1f}/{n} | {r['calls']:.1f} "
                f"| {r['tool_output']:,.0f} ({pct(r['tool_output'], base['tool_output'])}) "
                f"| {r['input']:,.0f} | {r['output']:,.0f} "
                f"| {total:,.0f} ({pct(total, base['input'] + base['output'])}) |"
            )
        print("\nAverages per run of all questions. % compared to MCP with pretty JSON.")
    return results


async def main(args):
    models = args.models or [core.MODEL]
    labs = {m: await core.format_lab(m) for m in models}
    for lab in labs.values():
        print_isolated(lab)

    e2e = await run_e2e(models, args.runs) if args.e2e else None

    if args.save:
        path = core.FOLDER / "runs" / "format_lab.json"
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps({"isolated": labs, "e2e": e2e}, indent=2), encoding="utf-8")
        print(f"\n💾 Saved {path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Does the output format change the cost?")
    parser.add_argument("--e2e", action="store_true", help="also run the end-to-end test (uses credits)")
    parser.add_argument("--runs", type=int, default=3, help="runs per question in the e2e test (default: 3)")
    parser.add_argument("--models", nargs="+", help="one or more models (results are never averaged across models)")
    parser.add_argument("--save", action="store_true", help="save results to runs/format_lab.json")
    args = parser.parse_args()
    if not core.has_api_key():
        raise SystemExit("❌ Needs ANTHROPIC_API_KEY (see .env.example).")
    asyncio.run(main(args))
