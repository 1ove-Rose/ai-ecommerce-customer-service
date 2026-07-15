from __future__ import annotations

import json

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from agents.intent_router import IntentCategory, IntentRouterAgent


class FakeLLM:
    def __init__(self, payload: dict):
        self.payload = payload
        self.calls = 0

    async def ainvoke(self, messages):
        self.calls += 1
        return AIMessage(content=json.dumps(self.payload, ensure_ascii=False))


@pytest.mark.asyncio
async def test_intent_router_routes_order_query_to_ticket_handler():
    agent = IntentRouterAgent(FakeLLM({
        "primary_intent": "logistics_query",
        "secondary_intent": "shipment_tracking",
        "confidence": 0.95,
        "entities": {"order_id": "ORD-10001"},
        "suggested_agent": "ticket_handler",
    }))

    result = await agent.classify("帮我查一下订单 ORD-10001 的物流")

    assert result.primary_intent == IntentCategory.LOGISTICS_QUERY
    assert result.suggested_agent == "ticket_handler"
    assert result.entities["order_id"] == "ORD-10001"


@pytest.mark.asyncio
async def test_intent_router_sanitizes_invalid_route():
    agent = IntentRouterAgent(FakeLLM({
        "primary_intent": "unknown_type",
        "secondary_intent": "unknown",
        "confidence": 0.2,
        "entities": {},
        "suggested_agent": "order_agent",
    }))

    result = await agent.classify("随便问问")

    assert result.primary_intent == IntentCategory.UNKNOWN
    assert result.suggested_agent == "knowledge_rag"


@pytest.mark.asyncio
async def test_intent_router_process_writes_graph_state():
    agent = IntentRouterAgent(FakeLLM({
        "primary_intent": "policy_faq",
        "secondary_intent": "return_policy",
        "confidence": 0.88,
        "entities": {},
        "suggested_agent": "knowledge_rag",
    }))

    state = {
        "messages": [HumanMessage(content="七天无理由退货规则是什么")],
        "intent": "",
        "sub_results": {},
    }

    next_state = await agent.process(state)

    assert next_state["intent"] == "knowledge_rag"
    assert next_state["sub_results"]["intent_router"]["primary"] == "policy_faq"


@pytest.mark.asyncio
async def test_intent_router_routes_greeting_to_smalltalk_without_llm():
    llm = FakeLLM({
        "primary_intent": "policy_faq",
        "secondary_intent": "return_policy",
        "confidence": 0.88,
        "entities": {},
        "suggested_agent": "knowledge_rag",
    })
    agent = IntentRouterAgent(llm)

    result = await agent.classify("你好")

    assert result.primary_intent == IntentCategory.GREETING
    assert result.suggested_agent == "smalltalk"
    assert llm.calls == 0


@pytest.mark.asyncio
async def test_intent_router_process_writes_smalltalk_response():
    agent = IntentRouterAgent(FakeLLM({}))

    state = {
        "messages": [HumanMessage(content="你好")],
        "intent": "",
        "sub_results": {},
    }

    next_state = await agent.process(state)

    assert next_state["intent"] == "smalltalk"
    assert next_state["sub_results"]["intent_router"]["primary"] == "greeting"
    assert "smalltalk" in next_state["sub_results"]
    assert "参考来源" not in next_state["sub_results"]["smalltalk"]


@pytest.mark.asyncio
async def test_intent_router_process_writes_identity_response():
    agent = IntentRouterAgent(FakeLLM({}))

    state = {
        "messages": [HumanMessage(content="你是谁")],
        "intent": "",
        "sub_results": {},
    }

    next_state = await agent.process(state)

    assert next_state["intent"] == "smalltalk"
    assert next_state["sub_results"]["intent_router"]["secondary"] == "identity"
    assert "电商客服多 Agent 系统" in next_state["sub_results"]["smalltalk"]
    assert "参考来源" not in next_state["sub_results"]["smalltalk"]
