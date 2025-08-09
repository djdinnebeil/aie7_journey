# app/tools.py
from __future__ import annotations
from typing import List
import asyncio
import os
from pathlib import Path
import logging

from langchain_community.tools.arxiv.tool import ArxivQueryRun
# (Optional) Tavily deprecation fix:
# pip install -U langchain-tavily
# from langchain_tavily import TavilySearch
# tavily_tool = TavilySearch(max_results=5)
from langchain_community.tools.tavily_search import TavilySearchResults

from app.rag import retrieve_information, _get_rag_graph
from langchain_core.tools import tool

# ---- simple demo tool (kept) ----
@tool
def word_count(text: str) -> dict:
    """Count characters, words, and lines in a string."""
    lines = text.splitlines()
    words = text.split()
    return {
        "characters": len(text),
        "words": len(words),
        "lines": len(lines),
        "preview": text[:120] + ("..." if len(text) > 120 else "")
    }

@tool
def tell_a_story_about_user():
    """Generate a made-up story about the user"""
    list_of_names = [
            'Katrina', 'Eric', 'Lily', 'Luna', 'Ray', 'Gianna', 'James', 'Tyler', 'Star', 'JJ',
            'Cefca', 'Gin 1', 'Tiger', 'Gin', 'Jace', 'Jose', 'RJ', 'DJ', 'Daniel', 'Emily',
            'Andrew', 'Kailie', 'Dana', 'Jessica', 'Rich', 'Dad', 'GJ', 'Gon', 'Gon', 'Emma',
            'Mair', 'Rune', 'Nova', 'Sol', 'Dune', 'Dinn', 'Ace', 'Acer', 'Iso', 'Iser',
            'Tide', 'Tile', 'Rise', 'Rye', 'Ryu', 'Lulu', 'Mom', 'Joanna', 'Justin', 'Paul',
            'Brian', 'Gina', 'Sarah', 'Megan', 'Jana', 'Cyndi', 'Beth', 'Danny', 'Del', 'Del'
        ]
    from datetime import datetime
    current_second = datetime.now().second
    name = list_of_names[current_second]
    graph = _get_rag_graph()
    result = graph.invoke({"question": f"Tell a made-up story about {name}"})

    return result
    


# ---- MCP wiring (robust) ----
try:
    from langchain_mcp_adapters.client import MultiServerMCPClient
except Exception:  # adapters not installed
    MultiServerMCPClient = None  # type: ignore

# Resolve the MCP server path relative to this file:
# repo_root/app/tools.py -> repo_root/weather_server.py
SERVER_PATH = (Path(__file__).resolve().parent.parent / "weather_server.py").as_posix()

async def _load_mcp_tools() -> List:
    if MultiServerMCPClient is None:
        logging.warning("MCP adapters not installed; skipping MCP tools.")
        return []

    if not os.path.exists(SERVER_PATH):
        logging.warning("MCP server not found at %s; skipping MCP tools.", SERVER_PATH)
        return []

    client = MultiServerMCPClient({
        "weather": {
            "command": "python",
            "args": [SERVER_PATH],
            "transport": "stdio",
        }
    })

    try:
        tools = await client.get_tools()
        return tools
    except Exception as e:
        logging.warning("Failed to load MCP tools (%s); continuing without them.", e)
        return []

_MCP_TOOLS: List | None = None

def _get_mcp_tools_sync() -> List:
    global _MCP_TOOLS
    if _MCP_TOOLS is None:
        try:
            _MCP_TOOLS = asyncio.run(_load_mcp_tools())
        except RuntimeError:
            # If already in an event loop (rare here), just skip MCP tools gracefully.
            logging.warning("Event loop in progress; skipping MCP tools load.")
            _MCP_TOOLS = []
    return _MCP_TOOLS

def get_tool_belt() -> List:
    """Tavily, Arxiv, RAG, demo tools, and (optionally) MCP tools."""
    tavily_tool = TavilySearchResults(max_results=5)
    base = [tavily_tool, ArxivQueryRun(), retrieve_information, word_count, tell_a_story_about_user]
    return base + _get_mcp_tools_sync()
