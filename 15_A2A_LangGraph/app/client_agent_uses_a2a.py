# app/client_agent_uses_a2a.py
from __future__ import annotations
import os
from typing import List
from uuid import uuid4

from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

# A2A client bits
import asyncio
import httpx
from a2a.client import A2ACardResolver, A2AClient
from a2a.types import MessageSendParams, SendMessageRequest
from a2a.utils.constants import AGENT_CARD_WELL_KNOWN_PATH

from dotenv import load_dotenv
load_dotenv()

A2A_BASE_URL = os.getenv('A2A_BASE_URL', 'http://localhost:10000')

async def _call_remote_agent_a2a(query: str) -> str:
    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as httpx_client:
        # Discover the Agent Card, then init client
        resolver = A2ACardResolver(httpx_client=httpx_client, base_url=A2A_BASE_URL)
        _ = await resolver.get_agent_card(relative_card_path=AGENT_CARD_WELL_KNOWN_PATH)
        client = A2AClient(httpx_client=httpx_client, agent_card=_)

        send_payload = {
            'message': {
                'role': 'user',
                'parts': [{'kind': 'text', 'text': query}],
                'message_id': uuid4().hex,
            },
        }
        req = SendMessageRequest(id=str(uuid4()), params=MessageSendParams(**send_payload))
        resp = await client.send_message(req)

        # Return the ‘result’ artifact text if present; otherwise a fallback
        try:
            return resp.root.result.artifacts[0].parts[0].root.text  # type: ignore
        except Exception:
            return 'No result text received from remote agent.'

@tool
def use_application(query: str) -> str:
    '''Call the remote A2A application (General Purpose Agent) with the user query.'''
    return asyncio.run(_call_remote_agent_a2a(query))

def build_client_agent():
    # This LLM won’t call Tavily/ArXiv directly; its only tool is "use_application".
    model = ChatOpenAI(model=os.getenv('CLIENT_MODEL', 'gpt-4o-mini'), temperature=0)
    tools: List = [use_application]
    return create_react_agent(model, tools)

if __name__ == '__main__':
    graph = build_client_agent()
    user_query = input('Enter a query: ')
    result = graph.invoke({'messages': [('user', user_query)]})
    print(result['messages'][-1].content)
