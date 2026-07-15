from __future__ import annotations

import json

import pytest
from langchain_core.messages import AIMessage

from agents.ticket_handler import TicketHandlerAgent


class FakeLLM:
    def __init__(self, payload: dict):
        self.payload = payload

    async def ainvoke(self, messages):
        return AIMessage(content=json.dumps(self.payload, ensure_ascii=False))


@pytest.mark.asyncio
async def test_ticket_handler_asks_for_order_id_when_missing():
    agent = TicketHandlerAgent(FakeLLM({
        "action": "order_query",
        "ticket_type": "order",
        "priority": "low",
        "summary": "查询订单",
        "details": "查询订单",
        "entities": {},
    }))

    ticket_info = await agent.analyze_request("查询订单")
    response = await agent.handle_ecommerce_action(ticket_info, user_id="u-1")

    assert "请提供" in response
    assert "订单号" in response
    assert "未找到订单" not in response


@pytest.mark.asyncio
async def test_ticket_handler_asks_for_order_id_when_logistics_missing():
    agent = TicketHandlerAgent(FakeLLM({
        "action": "logistics_query",
        "ticket_type": "logistics",
        "priority": "low",
        "summary": "查询物流",
        "details": "查询物流",
        "entities": {},
    }))

    ticket_info = await agent.analyze_request("查询物流")
    response = await agent.handle_ecommerce_action(ticket_info, user_id="u-1")

    assert "请提供" in response
    assert "订单号" in response
    assert "暂无物流信息" not in response