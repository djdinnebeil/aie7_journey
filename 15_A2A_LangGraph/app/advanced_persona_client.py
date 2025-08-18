# app/advanced_persona_client.py
"""
Advanced Agent (LangChain) with personas that uses your existing A2A server.

Implements the Advanced Build:
- Use a different Agent Framework (LangChain) to TEST your application.
- Create a Simple Agent that acts as different PERSONAS with different GOALS.
- Have that Agent USE your Agent through A2A.

Run examples (from repo root):
  uv run python app/advanced_persona_client.py --show-card
  uv run python app/advanced_persona_client.py --persona ml_researcher \
      --prompt "What makes Kimi K2 notable? Cite sources I can verify."
  uv run python app/advanced_persona_client.py --persona pm \
      --prompt "Summarize top differentiators of Kimi K2 for enterprise buyers."
  uv run python app/advanced_persona_client.py --persona educator \
      --prompt "Explain Kimi K2 for high school students with 3 simple examples."

Environment:
  OPENAI_API_KEY    (required for the LangChain LLM)
  A2A_BASE_URL      (default: http://localhost:10000)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
from typing import Any, Dict, List, Optional
from uuid import uuid4

import httpx
from dotenv import load_dotenv

# LangChain (different framework than your LangGraph app)
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

# A2A SDK
from a2a.client import A2ACardResolver  # ClientFactory imported lazily in code
from a2a.types import MessageSendParams, SendMessageRequest

# --------------------------------------------------------------------------------------
# Setup
# --------------------------------------------------------------------------------------
load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("advanced_persona_client")

A2A_BASE_URL = os.getenv("A2A_BASE_URL", "http://localhost:10000")


# --------------------------------------------------------------------------------------
# A2A helpers (async)
# --------------------------------------------------------------------------------------
async def _get_card(httpx_client: httpx.AsyncClient, base_url: str) -> Any:
    resolver = A2ACardResolver(httpx_client=httpx_client, base_url=base_url)
    return await resolver.get_agent_card()


async def _create_a2a_client(httpx_client: httpx.AsyncClient, card: Any) -> Any:
    """
    Prefer JSON-RPC via ClientFactory (new API), fall back to deprecated A2AClient.
    """
    try:
        from a2a.client import ClientFactory  # type: ignore

        factory = ClientFactory(httpx_client=httpx_client, agent_card=card)
        return await factory.create_jsonrpc_client()
    except Exception:
        # Fallback for older SDKs
        from a2a.client import A2AClient  # type: ignore

        return A2AClient(httpx_client=httpx_client, agent_card=card)


async def a2a_send_text(query: str, base_url: str = A2A_BASE_URL, timeout_s: float = 60.0) -> Any:
    """
    Send a single text message to the A2A server and return the typed response object.
    """
    async with httpx.AsyncClient(timeout=httpx.Timeout(timeout_s)) as httpx_client:
        card = await _get_card(httpx_client, base_url)
        client = await _create_a2a_client(httpx_client, card)

        payload = {
            "message": {
                "role": "user",
                "parts": [{"kind": "text", "text": query}],
                "message_id": uuid4().hex,
            }
        }
        req = SendMessageRequest(id=str(uuid4()), params=MessageSendParams(**payload))
        return await client.send_message(req)


def _safe_get(obj: Any, path: List[str]) -> Optional[Any]:
    """
    Safely traverse either typed SDK objects or dicts.
    E.g., path=['root','result','artifacts'].
    """
    cur = obj
    for key in path:
        if cur is None:
            return None
        # attribute-style
        if hasattr(cur, key):
            cur = getattr(cur, key)
            continue
        # dict-style
        if isinstance(cur, dict) and key in cur:
            cur = cur[key]
            continue
        return None
    return cur


def extract_text_from_a2a_response(resp: Any) -> str:
    """
    Preference order:
      1) Concatenate text from all artifact parts
      2) Fallback to status.message text (e.g., input-required)
      3) Fallback to result.text
      4) Dump a compact JSON of result
    """
    texts: List[str] = []

    # 1) Artifacts
    artifacts = _safe_get(resp, ["root", "result", "artifacts"]) or _safe_get(resp, ["result", "artifacts"])
    if artifacts:
        try:
            for art in artifacts:
                parts = getattr(art, "parts", None) or (art.get("parts") if isinstance(art, dict) else None)
                if not parts:
                    continue
                for p in parts:
                    # typed
                    if hasattr(p, "root") and hasattr(p.root, "text") and p.root.text:
                        texts.append(p.root.text)
                    # dict-ish
                    elif isinstance(p, dict):
                        t = p.get("root", {}).get("text") or p.get("text")
                        if t:
                            texts.append(t)
            if texts:
                return "\n\n".join(texts)
        except Exception:
            pass

    # 2) Status message
    status_msg_parts = _safe_get(resp, ["root", "result", "status", "message", "parts"]) or _safe_get(
        resp, ["result", "status", "message", "parts"]
    )
    if status_msg_parts:
        p0 = status_msg_parts[0]
        if hasattr(p0, "root") and hasattr(p0.root, "text") and p0.root.text:
            return p0.root.text
        if isinstance(p0, dict):
            t = p0.get("root", {}).get("text") or p0.get("text")
            if t:
                return t

    # 3) result.text
    result_text = _safe_get(resp, ["root", "result", "text"]) or _safe_get(resp, ["result", "text"])
    if result_text:
        return str(result_text)

    # 4) Compact JSON fallback
    try:
        # Try a compact dict representation if available
        if hasattr(resp, "model_dump"):
            return json.dumps(resp.model_dump(), indent=2)  # type: ignore
        if isinstance(resp, dict):
            return json.dumps(resp, indent=2)
    except Exception:
        pass
    return "(no text available)"


# --------------------------------------------------------------------------------------
# LangChain tool: make A2A available to the agent
# --------------------------------------------------------------------------------------
def make_a2a_tool():
    @tool
    def query_a2a_agent(query: str) -> str:
        """
        Query the remote A2A application and return user-visible text.
        Always use this when you need current info, sources, or document retrieval.
        """
        resp = asyncio.run(a2a_send_text(query))
        return extract_text_from_a2a_response(resp)

    return query_a2a_agent


# --------------------------------------------------------------------------------------
# Personas (goals/styles)
# --------------------------------------------------------------------------------------
PERSONAS: Dict[str, str] = {
    "ml_researcher": (
        "You are an expert in Machine Learning. Goal: dig beneath surface-level claims; "
        "demand sources and primary references. Prefer precise, technical language and "
        "short citations (URLs). If evidence is weak, say so explicitly."
    ),
    "pm": (
        "You are a product manager. Goal: identify user value, differentiators, and "
        "trade-offs. Be concise, prioritize impact, and call out risks with mitigation ideas."
    ),
    "security_auditor": (
        "You are a security auditor. Goal: assess risks, gaps, and threat models. "
        "Flag unverified claims and suggest verification steps. Be concrete."
    ),
    "educator": (
        "You are a patient educator. Goal: explain clearly in simple language with "
        "practical examples and a short reading list. Avoid jargon unless defined."
    ),
}


def persona_system_message(persona_key: str) -> SystemMessage:
    persona = PERSONAS.get(persona_key, PERSONAS["educator"])
    directive = (
        "You can use a powerful remote assistant via the tool `query_a2a_agent` that "
        "performs web search, academic paper lookup, and RAG over local docs. "
        "When you need facts, sources, or retrieval, you MUST call the tool to gather information, "
        "then synthesize the answer in your persona's style.\n\n"
        f"Persona instructions: {persona}"
    )
    return SystemMessage(content=directive)


# --------------------------------------------------------------------------------------
# Agent builder (LangChain)
# --------------------------------------------------------------------------------------
def build_langchain_persona_agent(persona_key: str):
    """
    Creates a minimal Functions-style agent with a single tool `query_a2a_agent`.
    The local LLM provides persona-specific reasoning; facts come from A2A.
    """
    llm = ChatOpenAI(model=os.getenv("CLIENT_MODEL", "gpt-4o-mini"), temperature=0)

    query_a2a_tool = make_a2a_tool()

    prompt = ChatPromptTemplate.from_messages(
        [
            persona_system_message(persona_key),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder("agent_scratchpad"),
        ]
    )

    agent = create_openai_functions_agent(llm=llm, tools=[query_a2a_tool], prompt=prompt)

    executor = AgentExecutor(
        agent=agent,
        tools=[query_a2a_tool],
        verbose=True,
        max_iterations=3,
        handle_parsing_errors=True,
    )
    return executor


# --------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Advanced Build — Personas agent (LangChain) using A2A")
    p.add_argument(
        "--persona",
        choices=list(PERSONAS.keys()),
        default="ml_researcher",
        help="Choose the persona/goal/style for the client agent",
    )
    p.add_argument("--prompt", required=False, default=None, help="User question/task for the persona agent")
    p.add_argument("--show-card", action="store_true", help="Print the Agent Card JSON and exit")
    return p.parse_args()


def main() -> int:
    args = parse_args()

    # Optional: show Agent Card quickly for the demo
    if args.show_card:
        async def _show():
            async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
                card = await _get_card(client, A2A_BASE_URL)
                # Try to serialize nicely
                for attr in ("model_dump_json", "to_json"):
                    if hasattr(card, attr):
                        try:
                            print(json.dumps(json.loads(getattr(card, attr)()), indent=2))
                            return
                        except Exception:
                            pass
                # Fallback best-effort
                try:
                    print(json.dumps(card if isinstance(card, dict) else card.model_dump(), indent=2))  # type: ignore
                except Exception:
                    print(card)
        asyncio.run(_show())
        return 0

    # Ensure OpenAI key exists for the LangChain LLM
    if not os.getenv("OPENAI_API_KEY"):
        log.error("OPENAI_API_KEY is not set. Add it to your environment or .env file.")
        return 1

    if not args.prompt:
        log.error("Please provide --prompt 'your question...'")
        return 1

    # Build and run the persona agent
    executor = build_langchain_persona_agent(args.persona)
    result = asyncio.run(executor.ainvoke({"input": args.prompt, "chat_history": []}))
    print("\n=== Persona Agent Answer ===\n")
    print(result["output"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
