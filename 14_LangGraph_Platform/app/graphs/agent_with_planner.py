"""
Agent with a Planner node + Tavily web search:
1) planner -> adds a brief system "PLAN" message (Answer directly | Use RAG | Use web search)
2) agent   -> model call (tool-enabled)
3) action  -> ToolNode (if tool_calls present)
...loops between agent <-> action until no more tool calls, then ends
"""
from __future__ import annotations
from typing import Dict, Any, List

from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import SystemMessage

# NEW: Tavily search tool
from langchain_community.tools.tavily_search import TavilySearchResults

from app.state import AgentState  # messages: Annotated[List, add_messages]
from app.models import get_chat_model  # central model getter
from app.tools import get_tool_belt    # shared tool belt


# --- Tools --------------------------------------------------------------------

# Minimal web search tool; requires TAVILY_API_KEY in env (no other changes needed).
_tavily_tool = TavilySearchResults(max_results=5)

def _all_tools() -> List:
    """Combine the existing project tool belt with Tavily web search."""
    return [*_safe_get_tool_belt(), _tavily_tool]

def _safe_get_tool_belt() -> List:
    try:
        tools = get_tool_belt()
        # Ensure list-like
        return list(tools) if tools is not None else []
    except Exception:
        # Fallback: still provide Tavily so the graph remains usable
        return []


# --- Model binding ------------------------------------------------------------

def _build_model_with_tools():
    model = get_chat_model()
    return model.bind_tools(_all_tools())


# --- Nodes --------------------------------------------------------------------

def planner(state: AgentState) -> Dict[str, Any]:
    """Add a compact plan as a SystemMessage to guide the next agent step.

    The planner must choose exactly one of:
      - Answer directly
      - Use RAG
      - Use web search (Tavily)
    """
    plan_llm = get_chat_model(model_name="gpt-4.1-mini", temperature=0)

    # Keep the prompt tiny but explicit so it consistently names one path.
    prompt = (
        "You are a planner. Given the latest user request and conversation so far, "
        "choose exactly ONE of these actions and explain in one short sentence:\n"
        "  1) Answer directly\n"
        "  2) Use RAG\n"
        "  3) Use web search (Tavily)\n\n"
        "Guidance:\n"
        "- Prefer 'Use RAG' for queries about the user's uploaded/corpus content "
        "(e.g., Amatol, Atlantic Loading Company, 'our corpus', 'uploaded sources').\n"
        "- Prefer 'Use web search (Tavily)' for general knowledge, current events, or "
        "when the answer likely isn't in the corpus.\n"
        "- Prefer 'Answer directly' for simple math/definitions/rewording that needs no lookup.\n\n"
        "Output format MUST be: PLAN: <Answer directly|Use RAG|Use web search (Tavily)> — <one-line reason>.\n\n"
        "Conversation (truncated to last 12 messages follows):"
    )
    convo_tail = state["messages"][-12:] if len(state["messages"]) > 12 else state["messages"]

    plan_msg = plan_llm.invoke([SystemMessage(content=prompt), *convo_tail])

    content = plan_msg.content.strip()
    # If the model forgot the prefix, normalize it so downstream nodes always see PLAN:
    if not content.startswith("PLAN:"):
        content = f"PLAN: {content}"

    return {"messages": [SystemMessage(content=content)]}


def call_agent(state: AgentState) -> Dict[str, Any]:
    """Main agent step (tool-enabled model)."""
    model = _build_model_with_tools()
    response = model.invoke(state["messages"])
    return {"messages": [response]}


def route_after_agent(state: AgentState):
    """If the last AI message called tools, go to action; else END."""
    last = state["messages"][-1]
    if getattr(last, "tool_calls", None):
        return "action"
    return END


# --- Graph --------------------------------------------------------------------

def build_graph():
    graph = StateGraph(AgentState)

    tool_node = ToolNode(_all_tools())
    graph.add_node("planner", planner)
    graph.add_node("agent", call_agent)
    graph.add_node("action", tool_node)

    graph.set_entry_point("planner")

    # planner -> agent
    graph.add_edge("planner", "agent")

    # agent -> (action | END)
    graph.add_conditional_edges("agent", route_after_agent, {"action": "action", END: END})

    # action -> agent (keep looping until tools are done)
    graph.add_edge("action", "agent")

    return graph


# Export compiled graph for LangGraph Platform
graph = build_graph().compile()
