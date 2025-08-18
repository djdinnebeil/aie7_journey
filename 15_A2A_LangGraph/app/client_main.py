"""
app/client_main.py

This script builds a LangGraph *client* that "uses" the running A2A application.
It offers two modes:
  • stategraph  – a minimal pass-through LangGraph graph (no local LLM)
  • react       – a tiny ReAct agent whose only tool is "use_application" (calls A2A)

Features for a clean video walkthrough:
  ✓ Clear step-by-step prints (Agent Card resolved, message sent, artifacts, etc.)
  ✓ Single-turn run with --prompt, or an interactive loop with --interactive
  ✓ Optional --demo that runs a short sequence of camera-ready prompts
  ✓ Robust event-loop handling for async A2A calls from a sync CLI

Usage examples (from repo root):
  uv run python app/client_main.py --show-card
  uv run python app/client_main.py --prompt "Find recent papers on multimodal transformers" \
                                  --mode stategraph
  uv run python app/client_main.py --mode react --interactive
  uv run python app/client_main.py --demo

Environment:
  A2A_BASE_URL   (default: http://localhost:10000)
  CLIENT_MODEL   (for react mode; default: gpt-4o-mini)

"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from typing import Any, Annotated, Dict, List, Optional, TypedDict
from uuid import uuid4

import httpx
from dotenv import load_dotenv

# LangGraph / LangChain imports (react mode + stategraph mode)
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

# A2A client SDK
from a2a.client import A2ACardResolver, A2AClient
from a2a.types import MessageSendParams, SendMessageRequest

load_dotenv()

# --------------------------------------------------------------------------------------
# Config & logging
# --------------------------------------------------------------------------------------
A2A_BASE_URL_DEFAULT = "http://localhost:10000"
A2A_BASE_URL = os.getenv("A2A_BASE_URL", A2A_BASE_URL_DEFAULT)

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("client_main")

# --------------------------------------------------------------------------------------
# Pretty printing helpers for the video
# --------------------------------------------------------------------------------------

def banner(title: str) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def step(msg: str, emoji: str = "•") -> None:
    print(f"{emoji} {msg}")


def ok(msg: str) -> None:
    print(f"  ✅ {msg}")


def warn(msg: str) -> None:
    print(f"  ⚠️  {msg}")


def err(msg: str) -> None:
    print(f"  ❌ {msg}")


# --------------------------------------------------------------------------------------
# A2A primitives (async) + safe sync wrappers
# --------------------------------------------------------------------------------------
async def _fetch_agent_card_async(base_url: str) -> Any:
    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as httpx_client:
        resolver = A2ACardResolver(httpx_client=httpx_client, base_url=base_url)
        return await resolver.get_agent_card()


def fetch_agent_card_sync(base_url: str) -> Any:
    """Resolve the (public) Agent Card from the server using a fresh event loop."""
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(_fetch_agent_card_async(base_url))
    finally:
        loop.close()


async def _send_message_async(base_url: str, text: str) -> Any:
    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as httpx_client:
        # 1) Resolve card
        resolver = A2ACardResolver(httpx_client=httpx_client, base_url=base_url)
        card = await resolver.get_agent_card()

        # 2) Create client
        client = A2AClient(httpx_client=httpx_client, agent_card=card)

        # 3) Build request
        payload = {
            "message": {
                "role": "user",
                "parts": [{"kind": "text", "text": text}],
                "message_id": uuid4().hex,
            }
        }
        req = SendMessageRequest(id=str(uuid4()), params=MessageSendParams(**payload))

        # 4) Send
        return await client.send_message(req)


def send_message_sync(base_url: str, text: str) -> Any:
    """Send one message to the A2A server using a fresh event loop."""
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(_send_message_async(base_url, text))
    finally:
        loop.close()


# --------------------------------------------------------------------------------------
# Result inspection / formatting (tries to be resilient to SDK versions)
# --------------------------------------------------------------------------------------

def extract_first_text(resp: Any) -> Optional[str]:
    """Best-effort extraction of the first text part from the A2A response."""
    try:
        # Expected path from many A2A SDKs
        artifacts = resp.root.result.artifacts  # type: ignore[attr-defined]
        if artifacts:
            parts = getattr(artifacts[0], "parts", None)
            if parts:
                part0 = parts[0]
                # Some SDKs wrap text under .root.text
                if hasattr(part0, "root") and hasattr(part0.root, "text"):
                    return part0.root.text
                # Fallbacks
                if hasattr(part0, "text"):
                    return part0.text
        # Sometimes there is a top-level text convenience
        if hasattr(resp.root.result, "text") and resp.root.result.text:
            return resp.root.result.text
    except Exception:
        pass
    return None


def print_a2a_summary(resp: Any) -> None:
    """Pretty-print a compact summary of the A2A response (for camera)."""
    try:
        result = resp.root.result  # type: ignore[attr-defined]
    except Exception:
        warn("Unexpected response structure; printing repr.")
        print(repr(resp))
        return

    # Task metadata
    task_id = getattr(result, "id", None)
    status = getattr(result, "status", None)
    if task_id or status:
        ok(f"Task: id={task_id} status={status}")

    # Artifacts
    artifacts = getattr(result, "artifacts", [])
    if not artifacts:
        warn("No artifacts present in result.")
        return

    step("Artifacts:")
    for i, art in enumerate(artifacts, 1):
        name = getattr(art, "name", "artifact")
        desc = getattr(art, "description", "")
        print(f"    {i:>2}. {name} — {desc}")
        parts = getattr(art, "parts", [])
        for p in parts[:1]:  # show only first part preview for brevity
            txt = None
            if hasattr(p, "root") and hasattr(p.root, "text"):
                txt = p.root.text
            elif hasattr(p, "text"):
                txt = p.text
            if txt:
                preview = (txt[:280] + "…") if len(txt) > 280 else txt
                print("        preview:")
                print("        " + preview.replace("\n", "\n        "))


# --------------------------------------------------------------------------------------
# MODE: StateGraph pass-through (no local LLM)
# --------------------------------------------------------------------------------------
class ClientState(TypedDict):
    messages: Annotated[List, add_messages]
    a2a_response: Any


def _client_node(state: ClientState, base_url: str) -> Dict[str, Any]:
    last = state["messages"][-1]
    user_text = getattr(last, "content", str(last))

    step("Sending message to A2A…")
    resp = send_message_sync(base_url, user_text)
    ok("Response received from A2A")

    # Pretty console view for the video
    print_a2a_summary(resp)

    # Also provide an AI message to satisfy graph contract
    display_text = extract_first_text(resp) or "(no text in artifacts)"
    return {"messages": [AIMessage(content=display_text)], "a2a_response": resp}


def build_stategraph_client(base_url: str):
    graph = StateGraph(ClientState)
    # Capture base_url via lambda closure
    graph.add_node("client", lambda s: _client_node(s, base_url))
    graph.set_entry_point("client")
    return graph.compile()


# --------------------------------------------------------------------------------------
# MODE: ReAct client with one tool (local LLM decides to call A2A)
# --------------------------------------------------------------------------------------
@tool
def use_application(query: str) -> str:
    """Call the remote A2A application with the user query and return text."""
    step("(tool) use_application → calling A2A…")
    resp = send_message_sync(A2A_BASE_URL, query)
    ok("(tool) A2A call complete")
    text = extract_first_text(resp)
    return text or "(no text in artifacts)"


def build_react_client() -> Any:
    model_name = os.getenv("CLIENT_MODEL", "gpt-4o-mini")
    model = ChatOpenAI(model=model_name, temperature=0)
    return create_react_agent(model, [use_application])


# --------------------------------------------------------------------------------------
# Demo prompts (camera-friendly)
# --------------------------------------------------------------------------------------
DEMO_PROMPTS = [
    ("Web Search", "What are 2–3 notable AI developments from 2024–2025?"),
    ("ArXiv", "Find recent papers on multimodal transformers and give one-sentence summaries."),
    ("RAG", "Using the local documents, what are 2 key insights? If none are loaded, say so.")
]


# --------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------

def parse_args(argv: List[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="A2A Demo Client (Activity #1)")
    p.add_argument("--base-url", default=A2A_BASE_URL, help=f"A2A server base URL (default: {A2A_BASE_URL})")
    p.add_argument("--mode", choices=["stategraph", "react"], default="stategraph",
                   help="Client mode: pass-through StateGraph or ReAct tool agent")
    p.add_argument("--prompt", default=None, help="Single prompt to send")
    p.add_argument("--interactive", action="store_true", help="Interactive prompt loop")
    p.add_argument("--demo", action="store_true", help="Run a short demo sequence of prompts")
    p.add_argument("--show-card", action="store_true", help="Fetch and display the Agent Card")
    return p.parse_args(argv)


def main(argv: List[str]) -> int:
    args = parse_args(argv)
    base_url = args.base_url

    banner("LangGraph Client • Using your A2A Application")
    step(f"Base URL: {base_url}")
    step(f"Mode: {args.mode}")

    # 1) Show Agent Card if requested
    if args.show_card:
        step("Resolving Agent Card…")
        try:
            card = fetch_agent_card_sync(base_url)
            ok("Agent Card resolved")
            # Try to print as JSON if possible
            dumped = None
            for attr in ("model_dump_json", "to_json"):
                if hasattr(card, attr):
                    try:
                        dumped = getattr(card, attr)()
                        break
                    except Exception:
                        pass
            if dumped is None:
                # Fallback: walk a few common attributes
                print("Card (partial):")
                for k in ("name", "description", "version", "url", "capabilities", "skills"):
                    v = getattr(card, k, None)
                    if v is not None:
                        print(f"  {k}: {v}")
            else:
                try:
                    # Pretty print JSON string
                    obj = json.loads(dumped)
                    print(json.dumps(obj, indent=2))
                except Exception:
                    print(dumped)
        except Exception as e:
            err(f"Failed to fetch Agent Card: {e}")
            return 1

        # If the user only requested --show-card, exit cleanly without showing --help
        if not (args.demo or args.prompt or args.interactive):
            return 0

    # 2) Build chosen client
    if args.mode == "stategraph":
        client = build_stategraph_client(base_url)
    else:
        client = build_react_client()

    # 3) Run flows
    try:
        if args.demo:
            banner("Demo run")
            for title, prompt in DEMO_PROMPTS:
                print(f"\n— {title} —")
                if args.mode == "stategraph":
                    result = client.invoke({"messages": [HumanMessage(content=prompt)], "a2a_response": None})
                    final = result["messages"][-1].content
                else:
                    result = client.invoke({"messages": [("user", prompt)]})
                    final = result["messages"][-1].content
                print("\nAnswer:\n" + str(final))
            return 0

        if args.prompt:
            banner("Single prompt")
            prompt = args.prompt
            if args.mode == "stategraph":
                result = client.invoke({"messages": [HumanMessage(content=prompt)], "a2a_response": None})
                final = result["messages"][-1].content
            else:
                result = client.invoke({"messages": [("user", prompt)]})
                final = result["messages"][-1].content
            print("\nAnswer:\n" + str(final))
            return 0

        if args.interactive:
            banner("Interactive mode (type 'exit' to quit)")
            while True:
                try:
                    user = input("You: ").strip()
                except (EOFError, KeyboardInterrupt):
                    print()
                    break
                if not user or user.lower() in {"exit", "quit"}:
                    break

                if args.mode == "stategraph":
                    result = client.invoke({"messages": [HumanMessage(content=user)], "a2a_response": None})
                    final = result["messages"][-1].content
                else:
                    result = client.invoke({"messages": [("user", user)]})
                    final = result["messages"][-1].content
                print("\nAnswer:\n" + str(final) + "\n")
            return 0

        # If nothing specified, show help
        warn("No action specified; showing --help")
        print()
        parse_args(["--help"])  # will print help and exit
        return 0

    except Exception as e:
        err(f"Client error: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
