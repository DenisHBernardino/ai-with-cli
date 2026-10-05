#!/usr/bin/env python3
"""
🏟️ The Arena: same question, three AIs, side by side in your browser.

  python app.py            # opens http://localhost:8000
  python app.py --record   # runs everything once and saves runs/demo.json
  python app.py --replay   # uses runs/demo.json even if you have an API key

The API key is read from the .env file (see .env.example) or from the terminal.

Modes:
  - LIVE:   you have ANTHROPIC_API_KEY -> real AI calls
  - REPLAY: no key, but runs/demo.json exists -> shows a real run that was recorded
  - OFFLINE: no key and no replay -> the page explains how to start

Only the Python standard library for the web part. No framework.
"""
import argparse
import asyncio
import json
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import core
from formats import FORMATS, LABELS

WEB_FILE = core.FOLDER / "web" / "index.html"
DEFAULT_REPLAY = core.FOLDER / "runs" / "demo.json"

state = {"mode": "offline", "replay": None, "costs": None, "lab": None}
costs_lock = threading.Lock()
lab_lock = threading.Lock()


# ================= recording a replay =================

async def record(path):
    """Run every test question in every mode once, plus the costs, and save it."""
    questions = core.load_questions()
    data = {"model": core.MODEL, "answers": {}, "costs": None}

    for item in questions:
        data["answers"][item["question"]] = {}

    # No tools and CLI
    for item in questions:
        q = item["question"]
        for mode in ["none", "cli"]:
            print(f"🎬 [{mode}] {q}")
            result = await core.ask(q, mode)
            result["correct"] = core.is_correct(result["answer"], item["expected"])
            data["answers"][q][mode] = result

    # MCP, once per output format
    for fmt in FORMATS:
        async with core.mcp_session(fmt) as session:
            mcp_tools = await core.get_mcp_tools(session)
            for item in questions:
                q = item["question"]
                print(f"🎬 [mcp, {fmt}] {q}")
                result = await core.ask(q, "mcp", session, mcp_tools)
                result["correct"] = core.is_correct(result["answer"], item["expected"])
                data["answers"][q][replay_key("mcp", fmt)] = result

    print("⏳ Counting the fixed cost for 3 to 50 tools...")
    data["costs"] = await core.all_costs()
    print("⏳ Running the output format lab...")
    data["format_lab"] = await core.format_lab()

    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ Saved {path}. Now anyone can run 'python app.py' without an API key.")


# ================= API =================

def replay_key(mode, fmt):
    """Where an answer lives in runs/demo.json: 'mcp' is pretty JSON, others are 'mcp:compact'..."""
    return mode if mode != "mcp" or fmt == "pretty" else f"mcp:{fmt}"


def api_status():
    return {
        "mode": state["mode"],
        "model": (state["replay"] or {}).get("model", core.MODEL),
        "questions": [q["question"] for q in core.load_questions()],
        "formats": [{"id": f, "label": LABELS[f]} for f in FORMATS],
    }


def api_ask(body):
    question = (body.get("question") or "").strip()
    mode = body.get("mode")
    fmt = body.get("fmt") or "pretty"
    if not question or mode not in core.MODES:
        return 400, {"error": "Send a question and a mode: none, cli or mcp."}
    if fmt not in FORMATS:
        return 400, {"error": f"Unknown format. Use one of: {', '.join(FORMATS)}"}

    if state["mode"] == "replay":
        recorded = state["replay"]["answers"].get(question)
        if not recorded:
            return 400, {"error": "Replay mode only has the test questions. Pick one of them."}
        key = replay_key(mode, fmt)
        if key not in recorded:
            return 400, {"error": "This replay has no recording for that format. Record it again with --record."}
        return 200, recorded[key]

    if state["mode"] == "offline":
        return 400, {"error": "No API key and no replay. See the setup steps on the page."}

    result = asyncio.run(core.ask_once(question, mode, fmt))
    expected = core.expected_for(question)
    result["correct"] = None if expected is None else core.is_correct(result["answer"], expected)
    return 200, result


def api_costs():
    if state["mode"] == "replay":
        return 200, state["replay"]["costs"]
    if state["mode"] == "offline":
        return 400, {"error": "Needs an API key or a replay to count tokens."}
    with costs_lock:  # count only once, then reuse
        if state["costs"] is None:
            state["costs"] = asyncio.run(core.all_costs())
    return 200, state["costs"]


def api_format_lab():
    if state["mode"] == "replay":
        lab = state["replay"].get("format_lab")
        if not lab:
            return 400, {"error": "This replay has no format lab. Record it again with --record."}
        return 200, lab
    if state["mode"] == "offline":
        return 400, {"error": "Needs an API key or a replay to count tokens."}
    with lab_lock:  # count only once, then reuse
        if state["lab"] is None:
            state["lab"] = asyncio.run(core.format_lab())
    return 200, state["lab"]


class Handler(BaseHTTPRequestHandler):
    def send_json(self, status, data):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/":
            body = WEB_FILE.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/api/status":
            self.send_json(200, api_status())
        elif self.path == "/api/costs":
            self.handle_errors(api_costs)
        elif self.path == "/api/format-lab":
            self.handle_errors(api_format_lab)
        else:
            self.send_json(404, {"error": "Not found"})

    def do_POST(self):
        if self.path != "/api/ask":
            return self.send_json(404, {"error": "Not found"})
        length = int(self.headers.get("Content-Length", 0))
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            return self.send_json(400, {"error": "Invalid JSON."})
        self.handle_errors(lambda: api_ask(body))

    def handle_errors(self, func):
        try:
            self.send_json(*func())
        except Exception as e:  # show the real error on the page, not a blank screen
            self.send_json(500, {"error": f"{type(e).__name__}: {e}"})

    def log_message(self, *args):
        pass  # keep the terminal clean


# ================= start =================

def main():
    parser = argparse.ArgumentParser(description="🏟️ The CLI vs MCP Arena.")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--record", action="store_true", help="record runs/demo.json (needs API key)")
    parser.add_argument("--replay", action="store_true", help="force replay mode")
    parser.add_argument("--replay-file", type=Path, default=DEFAULT_REPLAY)
    parser.add_argument("--no-browser", action="store_true", help="don't open the browser")
    args = parser.parse_args()

    if args.record:
        if not core.has_api_key():
            raise SystemExit("❌ Recording needs ANTHROPIC_API_KEY.")
        asyncio.run(record(args.replay_file))
        return

    if not WEB_FILE.exists():
        raise SystemExit(
            f"❌ Missing {WEB_FILE}\n"
            "   The web page must be inside a 'web' folder: web/index.html"
        )

    if not core.has_api_key():
        print("ℹ️  No API key found. Add it to the .env file (see .env.example).")

    if args.replay_file.exists() and (args.replay or not core.has_api_key()):
        state["mode"] = "replay"
        state["replay"] = json.loads(args.replay_file.read_text(encoding="utf-8"))
    elif core.has_api_key():
        state["mode"] = "live"

    url = f"http://localhost:{args.port}"
    print(f"🏟️  Arena running at {url}  (mode: {state['mode'].upper()})")
    print("   Press Ctrl+C to stop.")
    if not args.no_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()

    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Bye!")


if __name__ == "__main__":
    main()
