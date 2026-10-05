#!/usr/bin/env python3
"""
🧪 Experiment: how does the AI answer in 3 scenarios?

Asks the same questions in three modes:
  A) NO tools  -> the AI only has what it "remembers"
  B) WITH CLI  -> the AI can run the 'pizza' command in a terminal
  C) WITH MCP  -> the AI gets the tools from the MCP server

Each question runs several times (AI answers change), then we show the average.

  python experiment.py            # 3 runs (default)
  python experiment.py --runs 1   # faster and cheaper
"""
import argparse
import asyncio

import core

LABELS = {"none": "no tools", "cli": "with CLI", "mcp": "with MCP"}


async def main(runs):
    questions = core.load_questions()
    score = {m: {"correct": 0, "tokens": 0, "calls": 0} for m in core.MODES}

    async with core.mcp_session() as session:
        mcp_tools = await core.get_mcp_tools(session)

        for i, item in enumerate(questions, 1):
            print(f"\n❓ {i}. {item['question']}")
            for mode in core.MODES:
                marks = ""
                for run in range(runs):
                    result = await core.ask(item["question"], mode, session, mcp_tools)
                    ok = core.is_correct(result["answer"], item["expected"])
                    marks += "✅" if ok else "❌"
                    score[mode]["correct"] += ok
                    score[mode]["tokens"] += result["tokens"]
                    score[mode]["calls"] += result["calls"]
                    if run == 0:  # show the tools used in the first run
                        for step in result["trace"]:
                            icon = "🔧 AI ran:" if mode == "cli" else "🔌 AI called:"
                            print(f"     {icon} {step['call']}")
                summary = result["answer"].replace("\n", " ")[:90]
                print(f"  {marks} [{LABELS[mode]}] {summary}")

        print("\n⏳ Counting the fixed cost of each mode...")
        fixed = {
            "none": 0,
            "cli": core.fixed_cost([core.CLI_TOOL]),
            "mcp": core.fixed_cost(mcp_tools),
        }

    total = len(questions)
    print(f"\n📊 Results: average of {runs} run(s) (copy to the README)\n")
    print("| Mode | Correct | Tokens per run | Tool calls per run | Fixed cost per call |")
    print("|---|---|---|---|---|")
    for mode in core.MODES:
        s = score[mode]
        correct = s["correct"] / runs
        print(
            f"| {LABELS[mode]} | {correct:.1f}/{total} | {s['tokens'] // runs:,} "
            f"| {s['calls'] / runs:.1f} | {fixed[mode]:,} tokens |"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the CLI vs MCP experiment.")
    parser.add_argument("--runs", type=int, default=3, help="times to repeat each question (default: 3)")
    asyncio.run(main(parser.parse_args().runs))
