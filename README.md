# 🍕 AI with CLI and MCP: why it gets more answers right

🇺🇸 English | 🇧🇷 [Português](README.pt-BR.md)

[![tests](https://github.com/DenisHBernardino/ai-with-cli/actions/workflows/tests.yml/badge.svg)](https://github.com/DenisHBernardino/ai-with-cli/actions/workflows/tests.yml)

A simple experiment to show one idea:

> **An AI without access to data makes things up. With a CLI or an MCP to check, it gets it right.**

Here, the AI works at **Nona Byte Pizza**, a fake pizza shop.
It has no way to "know" the menu.
So we ask the same questions in 3 scenarios:

- **No tools:** the AI only has its own memory.
- **With CLI:** the AI runs the `pizza` command in a terminal.
- **With MCP:** the AI gets ready-made "buttons" from an MCP server.

Then we compare correct answers and cost.

![The Arena: same question, three AIs side by side](docs/arena-en.gif)

**Fastest way to see it:** run `python app.py` and open **The Arena** in your browser. 🏟️

---

## 🧠 CLI or MCP? Think of a pizza shop

![CLI is ordering at the counter, MCP is a delivery app](docs/cli-vs-mcp.svg)

**CLI = ordering at the counter.**
You say it directly: "one large Margherita".
It is fast and cheap. But you need to be there and know how to order.

**MCP = a delivery app.**
It has buttons, login and payment. Anyone can use it, from anywhere.
But the app loads the full menu every time it opens.

For the AI, this "menu" is the tool descriptions.
They are sent with **every** question, and they cost tokens.

---

## 🧭 Which one should I use?

```mermaid
flowchart TD
    A[The AI needs real data] --> B{Does it have a terminal?}
    B -- No, it is a chat app --> MCP[🔌 Use MCP]
    B -- Yes --> C{Is there a good CLI already?<br/>git, docker, gh, aws...}
    C -- Yes --> CLI[🖥️ Use CLI]
    C -- No --> D{Many tools, non-dev users<br/>or login needed?}
    D -- Yes --> MCP
    D -- No --> CLI2[🖥️ Build a simple CLI]
```

| Situation | Best choice |
|---|---|
| Coding agent in your project | 🖥️ CLI |
| Tool that already has a CLI (git, docker, gh, aws) | 🖥️ CLI |
| You want to spend few tokens | 🖥️ CLI |
| Chat app, no terminal | 🔌 MCP |
| Many tools or APIs | 🔌 MCP |
| Team with people who don't code | 🔌 MCP |
| You need login, permissions and audit logs | 🔌 MCP |

**It's not a war.** Many projects use both.

---

## 📁 Project structure

| File | What it does |
|---|---|
| `pizza.py` | The CLI. Reads the menu and answers commands. |
| `mcp_server.py` | The MCP server. Same data, delivered as tools. |
| `core.py` | Shared logic: talks to the AI, runs tools, counts tokens. |
| `app.py` + `web/index.html` | 🏟️ The Arena: the web page. |
| `experiment.py` | The terminal version: all questions, many runs, a score table. |
| `format_lab.py` + `formats.py` | 📦 The output format lab: same data in 3 formats. |
| `.env.example` | Template for your `.env` file with the API key. |
| `data.json` | The menu (our "database"). |
| `questions.json` | The test questions and the right answers. |
| `runs/demo.json` | A recorded real run, for replay mode (you create it). |
| `tests/` | Automated tests (run on GitHub Actions). |
| `docs/cli-vs-mcp.svg` | The infographic above. |

---

## 🚀 Step by step

### 1. Clone and install

```bash
git clone https://github.com/DenisHBernardino/ai-with-cli.git
cd ai-with-cli
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

You need Python 3.10 or newer.

### 2. Play with the CLI yourself

Before the AI, try it yourself. This is what the AI will use.

```bash
python pizza.py --help
python pizza.py menu
python pizza.py menu --vegetarian
python pizza.py search mushroom
python pizza.py price four cheese --size L
python pizza.py price pepperoni --json
```

### 3. Add your API key

Get a key at [console.anthropic.com](https://console.anthropic.com) (Settings > API keys).

Copy the example file and paste your key into it:

```bash
cp .env.example .env          # Windows: copy .env.example .env
```

```
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

The `.env` file is in `.gitignore`, so it **never** goes to GitHub.
No key? Skip this step: the tests and the CLI work without it.

### 4. Open the Arena 🏟️

```bash
python app.py
```

Your browser opens at `http://localhost:8000`.

- Click a question. The 3 AIs answer side by side.
- Watch the CLI column: the AI runs `pizza --help` **by itself** to learn the tool.
- Watch the "No tools" column: it answers with confidence, but it has no data.
- Drag the **hidden cost** slider from 3 to 50 MCP tools. The token bar grows. These are real counts from the API.

### 5. No API key? Use replay mode

Someone with a key records one real run:

```bash
python app.py --record      # saves runs/demo.json
```

Commit `runs/demo.json`. Now anyone can run `python app.py` **without a key**.
The page shows a "Replay of a real run" badge, so nobody thinks it is live.

### 6. Run the full experiment in the terminal

```bash
python experiment.py              # each question 3 times
python experiment.py --runs 1     # faster and cheaper
```

AI answers change from run to run, so the score is an average.

```
❓ 1. How much is a large Margherita?
     🔧 AI ran: pizza --help
     🔧 AI ran: pizza price margherita --size L
  ❌❌❌ [no tools] I don't have access to the current menu...
  ✅✅✅ [with CLI] A large Margherita costs $52.00.
     🔌 AI called: get_price({"pizza": "Margherita", "size": "L"})
  ✅✅✅ [with MCP] A large Margherita costs $52.00.
```

*(Example only. Your results will be different.)*

At the end, you get the score. Paste yours here. 👇

| Mode | Correct | Tokens per run | Tool calls per run | Fixed cost per call |
|---|---|---|---|---|
| no tools | ? / 6 | ? | 0 | 0 tokens |
| with CLI | ? / 6 | ? | ? | ? tokens |
| with MCP | ? / 6 | ? | ? | ? tokens |

**Fixed cost** = tokens the tool descriptions add to **every** call.

### 7. Run the tests

```bash
python -m unittest discover -s tests -t . -v
```

No API key needed. GitHub Actions runs them on every push.

---

## 🔍 What to look for in the results

**1. With no tools, the AI can't get it right.**
The menu is fake. The AI either guesses or says "I don't know". A good model usually refuses to guess, which is honest, but it still can't help.

**2. CLI and MCP learn the tool in different ways.**
The CLI AI often reads `--help` first, like a developer reading the docs.
The MCP AI skips that step, because MCP tools arrive already described. It goes straight to calling them.

**3. Output size drives the cost.**
In our tests, MCP spent more tokens than the CLI, even with only 3 tools.
The reason: the CLI answers with short text, and the MCP tools answer with full JSON.

Example from one real run (`claude-sonnet-5-5`):

| Question | CLI | MCP |
|---|---|---|
| "How much is a medium Ham & Egg plus a large Four Cheese?" | 1,352 tokens, 2 calls | 2,063 tokens, 2 calls |
| "Explore the tool, then tell me 3 ways you can help." | 3,444 tokens, 5 calls | 4,847 tokens, 4 calls |

In the second question, the CLI AI ran `pizza --help`, then `--help` for each command, then `pizza menu`.
The MCP AI called `list_menu` 3 times and got back 112, 64 and 97 lines of JSON.

*AI answers change on every run. Run your own and compare.*

**4. More tools = a bigger hidden cost.**
Drag the slider in the Arena from 3 to 50 tools. MCP sends all tool descriptions with every question.

---

## 💬 Questions to try

Type these in the Arena. They need several steps, so you see the AI really explore the tool.

| Question | What it shows | Expected answer |
|---|---|---|
| Before answering, explore what the pizza tool can do. Then tell me 3 ways you can help me. | How each AI learns the tool | Free answer |
| I want a Pepperoni. If I can't have it, what's the closest pizza available today? | Finds that Pepperoni is sold out, compares ingredients | Ham & Egg |
| I'm vegetarian and I have $40. What medium pizza can I order today? | Filter + price + availability | Banana Cinnamon ($38) |
| I'm allergic to onion. Which pizzas can I eat, and which is the cheapest large one? | Excludes ingredients | Banana Cinnamon ($48) |
| Which ingredient appears in the most pizzas? | Reads the whole menu and counts | Mozzarella (6 of 7) |
| Plan a party: 2 large pizzas, one vegetarian and one with meat, only available ones, cheapest total. | Planning | Banana Cinnamon + Chicken & Cream Cheese = $102 |

---

## 📦 The output format lab

In our first runs, MCP spent more tokens than the CLI. The traces suggested a reason: the CLI answers with short text, and the MCP tools answered with pretty JSON. But the totals mixed many things: tool output size, the length of the AI's own answer, and the number of calls.

So the lab separates them.

**Part 1: isolated test.** The same 5 tool calls, the same MCP server, the same data. Only the output format changes. No AI answer is generated: we only count tokens with the API. **The format is the only variable.**

| Format | What the AI receives |
|---|---|
| Pretty JSON | JSON with line breaks and indentation |
| Compact JSON | The same JSON, with no spaces |
| Plain text | Short text, exactly what the CLI prints |

**Part 2: end-to-end test.** The 6 test questions answered by the AI, with MCP in each format, plus the CLI. Tokens are split into three numbers:

- **Tool output:** only what the tools sent back, counted once each.
- **AI read:** everything the AI read (question, tool descriptions, tool outputs and history).
- **AI wrote:** everything the AI wrote (its answer and its tool calls).

Results are shown **per model**, never averaged across models.

```bash
python format_lab.py                          # part 1 only (just token counting)
python format_lab.py --e2e --runs 3           # part 1 + part 2
python format_lab.py --e2e --models claude-sonnet-5-5 claude-haiku-4-5
python format_lab.py --e2e --save             # also saves runs/format_lab.json
```

In the Arena you can see it too:

- The **"MCP tools answer in"** switch changes the format of the MCP column.
- Each column shows **📦 tokens of tool output**, separate from the total.
- The **output format lab** section shows part 1 with bars.

### Our results

Model `claude-sonnet-5-5`, 6 questions, 3 runs per question, per setup.

**Part 1: isolated (format is the only variable)**

| Format | Tool output tokens (5 calls) | vs pretty JSON |
|---|---|---|
| Pretty JSON | 2,281 | 0% |
| Compact JSON | 1,479 | -35% |
| Plain text | 1,101 | -52% |

**Part 2: end-to-end (averages per run of all 6 questions)**

| Setup | Correct | Tool calls | Tool output | AI read | AI wrote | Total |
|---|---|---|---|---|---|---|
| CLI* | 6.0/6 | 7.7 | 4,541 | 11,630 | 825 | 12,455 (-13%) |
| MCP, Pretty JSON | 6.0/6 | 8.0 | 3,231 | 13,384 | 939 | 14,323 (0%) |
| MCP, Compact JSON | 6.0/6 | 8.0 | 2,099 | 12,252 | 881 | 13,133 (-8%) |
| MCP, Plain text | 6.0/6 | 8.0 | 1,544 | 11,696 | 894 | 12,589 (-12%) |

**What we learned**

1. **The format alone matters a lot.** Same data: 35% fewer tokens as compact JSON, 52% fewer as plain text.
2. **Shorter formats didn't hurt accuracy.** Every setup got 18 out of 18 right.
3. **End to end, the gain is smaller (8% to 12%).** Tool output is only about a quarter of what the AI reads. The rest is the system prompt, the tool descriptions and the history, which is sent again on every round.
4. **With plain text, MCP almost ties with the CLI** (12,589 vs 12,455 tokens).
5. **The AI copies the examples in your tool description.** The CLI returned more tool output (4,541 vs 1,544). The traces showed why: the CLI tool description had `menu --json` as an example, and the AI ran `pizza menu --json` in most questions, getting pretty JSON back. It read `--help` only once. We removed `--json` from the example.
6. **The format changes the answer, not only the cost.** With JSON, the AI said "52", because the JSON has no currency. With text, it said "$52.00". The AI repeats what it sees.
7. **Our first number was too high.** One question, one run showed MCP costing about 40% more. With 6 questions and 3 runs, the gap with pretty JSON is 13%.

\* *This run used the old CLI description with `menu --json` as an example. Run `python format_lab.py --e2e` again to see the CLI with plain text.*

*Limits: one model, a small menu and easy questions. Try other models with `--models`.*

**What it does not measure:** whether a format makes the AI understand the data better or worse in harder tasks. That's why part 2 also shows correct answers.

---

## ✨ What makes a tool good for AI

This works for both CLI and MCP:

| Detail | In the CLI | In the MCP |
|---|---|---|
| Explains how to use it | `--help` with examples | Clear description for each tool |
| Output easy to read | Short text (`--json` when needed) | Short text or compact JSON |
| Error with a hint | `Hint: run 'menu'` | `Hint: use list_menu` |
| Can't break anything | Read-only + allowed commands | Read-only |

---

## ⚖️ Honest notes

- **With tools, the AI spends more tokens than without.** It checks data and reads output. The gain is **accuracy**.
- **CLI does not always win.** With many tools, some studies show MCP with a higher success rate.
- **A bad tool gets in the way.** Without a good description and clear errors, the AI gets lost, with CLI or MCP.

Further reading:
- [MCP vs CLI: a real AWS benchmark (dev.to)](https://dev.to/webramos/mcp-vs-cli-for-ai-agents-a-real-aws-benchmark-and-why-the-popular-narrative-asks-the-wrong-4h8)
- [MCP vs CLI: which one to use in 2026 (Firecrawl)](https://www.firecrawl.dev/blog/mcp-vs-cli)
- [MCP vs CLI: which is better for agentic AI (Nordic APIs)](https://nordicapis.com/mcp-vs-cli-which-is-better-for-agentic-ai/)
- [MCP vs CLI for AI agents: enterprise guide (Tyk)](https://tyk.io/learning-center/mcp-vs-cli-for-ai-agents-enterprise-comparison-guide/)

---

## 🎯 Challenges for you

1. Remove the examples from `--help`. Does the CLI AI make more mistakes?
2. Delete the MCP tool descriptions. What changes?
3. Add a 4th format to `formats.py` that returns only the fields needed. Does it beat plain text?
4. Open `core.py` and change the fake tool descriptions. Does the slider change?
5. Add a `pizza combo` command and a `combo` tool with a discount.
6. Set Pepperoni `available` to `true` and run it again.


## 📄 License

MIT. Use it, copy it, teach it. 🍕
