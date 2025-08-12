"""Toolbelt assembly for agents.

Collects third-party tools and local tools (like RAG) into a single list that
graphs can bind to their language models.
"""
from __future__ import annotations
from typing import List
import asyncio

from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_community.tools.arxiv.tool import ArxivQueryRun
from langchain_mcp_adapters.client import MultiServerMCPClient

from app.rag import retrieve_information
from app.custom_tools import tell_a_story_about_user


def get_tool_belt() -> List:
    """Return the list of tools available to agents (Tavily, Arxiv, RAG, custom, MCP)."""
    base_tools = [
        TavilySearchResults(max_results=5),
        ArxivQueryRun(),
        retrieve_information,
        tell_a_story_about_user
    ]

    # Create MCP client and get tools synchronously
    client = MultiServerMCPClient({
        "weather": {
            "command": "python",
            "args": ["./weather_server.py"],
            "transport": "stdio",
        }
    })
    mcp_tools = asyncio.run(client.get_tools())

    return base_tools + mcp_tools
