"""
工单处理 Agent — 电商事务动作编排
负责处理订单查询、物流查询、退款/退换货、投诉和转人工等需要业务动作的客服请求。
后续通过 MCP 工具协议调用订单、物流、售后、工单等外部系统。
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, TYPE_CHECKING

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from tracing.otel_config import trace_agent_call

if TYPE_CHECKING:
    from mcp.mcp_server import MCPToolServer


class TicketStatus(str, Enum):
    CREATED = "created"
    PROCESSING = "processing"
    PENDING_REVIEW = "pending_review"
    RESOLVED = "resolved"
    CLOSED = "closed"
    ESCALATED = "escalated"


class TicketPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


TICKET_SYSTEM_PROMPT = """你是一个电商客服事务处理 Agent，负责把用户请求转换成可执行的电商业务动作。

你的职责：
1. 识别用户想要执行的动作
2. 提取订单号、物流单号、售后单号、商品名、问题描述等关键字段
3. 对需要人工介入的投诉、异常售后、强烈不满创建工单
4. 在 MCP 工具接入前，输出稳定的结构化动作，供后续工具层执行

可用动作：
- order_query: 查询订单详情或订单状态
- logistics_query: 查询物流轨迹或配送状态
- after_sale_create: 创建退款、退货、换货、维修等售后申请
- after_sale_query: 查询售后进度
- ticket_create: 创建人工工单或投诉工单
- ticket_query: 查询已有工单
- human_handoff: 转人工

优先级判断规则：
- urgent: 严重投诉、疑似欺诈、用户明确要求立即人工介入
- high: 退款超时、物流异常、商品破损、重复投诉
- medium: 常规订单、物流、售后处理
- low: 普通咨询或状态查询

请只以 JSON 格式返回：
{
    "action": "order_query|logistics_query|after_sale_create|after_sale_query|ticket_create|ticket_query|human_handoff",
    "ticket_type": "order|logistics|refund|return_exchange|complaint|human|general",
    "priority": "low|medium|high|urgent",
    "summary": "摘要",
    "details": "详细描述",
    "entities": {
        "order_id": "订单号",
        "tracking_no": "物流单号",
        "after_sale_id": "售后单号",
        "product": "商品名"
    }
}
"""


class TicketStore:
    """内存工单存储（生产环境应替换为数据库）"""

    def __init__(self):
        self._tickets: dict[str, dict] = {}

    def create(self, ticket_type: str, priority: str, summary: str, details: str, user_id: str) -> dict:
        ticket_id = f"TK-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        ticket = {
            "ticket_id": ticket_id,
            "type": ticket_type,
            "priority": priority,
            "status": TicketStatus.CREATED.value,
            "summary": summary,
            "details": details,
            "user_id": user_id,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        self._tickets[ticket_id] = ticket
        return ticket

    def query(self, ticket_id: str) -> dict | None:
        return self._tickets.get(ticket_id)

    def query_by_user(self, user_id: str) -> list[dict]:
        return [t for t in self._tickets.values() if t["user_id"] == user_id]

    def update_status(self, ticket_id: str, status: str) -> dict | None:
        ticket = self._tickets.get(ticket_id)
        if ticket:
            ticket["status"] = status
            ticket["updated_at"] = datetime.now().isoformat()
        return ticket


class TicketHandlerAgent:
    """工单处理Agent"""

    def __init__(
        self,
        llm: ChatOpenAI,
        ticket_store: TicketStore | None = None,
        mcp_server: MCPToolServer | None = None,
    ):
        self.llm = llm
        self.ticket_store = ticket_store or TicketStore()
        self.mcp_server = mcp_server

    @trace_agent_call("ticket_analyze")
    async def analyze_request(self, user_message: str) -> dict:
        """分析用户需求，提取工单信息"""
        messages = [
            SystemMessage(content=TICKET_SYSTEM_PROMPT),
            HumanMessage(content=f"用户消息: {user_message}"),
        ]

        response = await self.llm.ainvoke(messages)

        import json
        content = response.content.strip()
        if content.startswith("```"):
            content = content.strip("`")
            if content.startswith("json"):
                content = content[4:].strip()
        try:
            result = json.loads(content)
        except json.JSONDecodeError:
            result = {
                "action": "ticket_create",
                "ticket_type": "general",
                "priority": "medium",
                "summary": user_message[:100],
                "details": user_message,
                "entities": {},
            }

        valid_actions = {
            "order_query",
            "logistics_query",
            "after_sale_create",
            "after_sale_query",
            "ticket_create",
            "ticket_query",
            "human_handoff",
        }
        if result.get("action") not in valid_actions:
            result["action"] = "ticket_create"
        result.setdefault("entities", {})
        return result

    @trace_agent_call("ticket_create")
    async def create_ticket(self, ticket_info: dict, user_id: str) -> str:
        """创建工单"""
        ticket = self.ticket_store.create(
            ticket_type=ticket_info.get("ticket_type", "general"),
            priority=ticket_info.get("priority", "medium"),
            summary=ticket_info.get("summary", ""),
            details=ticket_info.get("details", ""),
            user_id=user_id,
        )

        priority_label = {
            "low": "普通", "medium": "中等", "high": "高", "urgent": "紧急"
        }.get(ticket["priority"], "中等")

        return (
            f"工单已创建成功！\n\n"
            f"📋 工单号: {ticket['ticket_id']}\n"
            f"📝 类型: {ticket['type']}\n"
            f"⚡ 优先级: {priority_label}\n"
            f"📄 摘要: {ticket['summary']}\n"
            f"🕐 创建时间: {ticket['created_at']}\n\n"
            f"我们将尽快处理您的请求，请保存好工单号以便后续查询。"
        )

    @trace_agent_call("ticket_query")
    async def query_ticket(self, ticket_id: str) -> str:
        """查询工单状态"""
        ticket = self.ticket_store.query(ticket_id)
        if not ticket:
            return f"未找到工单号 {ticket_id}，请确认工单号是否正确。"

        status_label = {
            "created": "已创建",
            "processing": "处理中",
            "pending_review": "待审核",
            "resolved": "已解决",
            "closed": "已关闭",
            "escalated": "已升级",
        }.get(ticket["status"], ticket["status"])

        return (
            f"工单查询结果：\n\n"
            f"📋 工单号: {ticket['ticket_id']}\n"
            f"📊 状态: {status_label}\n"
            f"📝 类型: {ticket['type']}\n"
            f"📄 摘要: {ticket['summary']}\n"
            f"🕐 创建时间: {ticket['created_at']}\n"
            f"🔄 更新时间: {ticket['updated_at']}"
        )

    async def _call_mcp_tool(self, name: str, arguments: dict[str, Any]) -> dict | None:
        """调用 MCP 工具；工具不可用或失败时返回 None，由本地 fallback 接管。"""
        if self.mcp_server is None:
            return None
        result = await self.mcp_server.call_tool(name, arguments)
        if not result.success:
            return None
        return result.result

    async def handle_ecommerce_action(self, ticket_info: dict, user_id: str) -> str:
        """处理电商事务动作；优先通过 MCP 工具执行。"""
        action = ticket_info.get("action", "ticket_create")
        entities = ticket_info.get("entities", {}) or {}

        if action == "order_query":
            order_id = entities.get("order_id", "")
            if not order_id:
                return "请提供需要查询的订单号，我会继续为您查询订单状态。"
            tool_result = await self._call_mcp_tool("order_query", {"order_id": order_id})
            if tool_result:
                if not tool_result.get("found", True):
                    return tool_result.get("message", f"未找到订单 {order_id}")
                order = tool_result.get("order", {})
                return (
                    f"订单查询结果：\n\n"
                    f"订单号: {order.get('id', order_id)}\n"
                    f"订单状态: {order.get('status', '未知')}\n"
                    f"支付状态: {order.get('payment_status', '未知')}\n"
                    f"订单金额: {order.get('total_amount', '未知')}\n"
                    f"商品: {', '.join(item.get('product_name', '') for item in order.get('items', [])) or '暂无明细'}"
                )
            return (
                f"已识别为订单查询请求。\n\n"
                f"订单号: {order_id or '未提供'}\n"
                f"当前 MCP 订单工具不可用，后续会接入真实订单数据。"
            )

        if action == "logistics_query":
            order_id = entities.get("order_id", "")
            if not order_id:
                return "请提供需要查询物流的订单号，我会继续为您查询配送进度。"
            tool_result = await self._call_mcp_tool("logistics_query", {"order_id": order_id})
            if tool_result:
                if not tool_result.get("found", True):
                    return tool_result.get("message", f"订单 {order_id} 暂无物流信息")
                events = tool_result.get("events", [])
                latest_event = events[-1].get("message") if events else "暂无轨迹"
                return (
                    f"物流查询结果：\n\n"
                    f"订单号: {tool_result.get('order_id', order_id)}\n"
                    f"物流公司: {tool_result.get('carrier', '未知')}\n"
                    f"物流单号: {tool_result.get('tracking_no', '未知')}\n"
                    f"物流状态: {tool_result.get('status', '未知')}\n"
                    f"预计送达: {tool_result.get('eta') or '暂无'}\n"
                    f"最新轨迹: {latest_event}"
                )
            return (
                f"已识别为物流查询请求。\n\n"
                f"订单号: {order_id or '未提供'}\n"
                f"当前 MCP 物流工具不可用，后续会接入真实物流轨迹。"
            )

        if action == "after_sale_create":
            order_id = entities.get("order_id", "")
            tool_result = await self._call_mcp_tool(
                "after_sale_create",
                {
                    "user_id": user_id,
                    "order_id": order_id,
                    "type": ticket_info.get("ticket_type", "refund"),
                    "reason": ticket_info.get("details", "用户申请售后"),
                },
            )
            if tool_result:
                return (
                    f"售后申请已创建：\n\n"
                    f"售后单号: {tool_result.get('id')}\n"
                    f"订单号: {tool_result.get('order_id')}\n"
                    f"类型: {tool_result.get('type')}\n"
                    f"状态: {tool_result.get('status')}"
                )
            return await self.create_ticket(ticket_info, user_id)

        if action == "after_sale_query":
            after_sale_id = entities.get("after_sale_id", "")
            tool_result = await self._call_mcp_tool("after_sale_query", {"after_sale_id": after_sale_id})
            if tool_result:
                if not tool_result.get("found", True):
                    return tool_result.get("message", f"未找到售后单 {after_sale_id}")
                after_sale = tool_result.get("after_sale", {})
                return (
                    f"售后进度查询结果：\n\n"
                    f"售后单号: {after_sale.get('id', after_sale_id)}\n"
                    f"订单号: {after_sale.get('order_id', '未知')}\n"
                    f"类型: {after_sale.get('type', '未知')}\n"
                    f"状态: {after_sale.get('status', '未知')}"
                )
            return "请提供正确的售后单号，我会继续为您查询。"

        if action in {"human_handoff", "ticket_create"}:
            tool_result = await self._call_mcp_tool(
                "ticket_create",
                {
                    "user_id": user_id,
                    "order_id": entities.get("order_id"),
                    "type": ticket_info.get("ticket_type", "general"),
                    "priority": ticket_info.get("priority", "medium"),
                    "summary": ticket_info.get("summary", "客服工单"),
                    "details": ticket_info.get("details", ""),
                },
            )
            if tool_result:
                return (
                    f"工单已创建成功！\n\n"
                    f"工单号: {tool_result.get('id')}\n"
                    f"类型: {tool_result.get('type')}\n"
                    f"优先级: {tool_result.get('priority')}\n"
                    f"状态: {tool_result.get('status')}\n"
                    f"摘要: {tool_result.get('summary')}"
                )
            return await self.create_ticket(ticket_info, user_id)

        if action == "ticket_query":
            ticket_id = entities.get("ticket_id") or ticket_info.get("ticket_id")
            if ticket_id:
                return await self.query_ticket(ticket_id)
            return "请提供需要查询的工单号。"

        return await self.create_ticket(ticket_info, user_id)

    @trace_agent_call("ticket_handler_process")
    async def process(self, state: dict[str, Any]) -> dict[str, Any]:
        """作为Graph节点处理状态"""
        messages = state.get("messages", [])
        user_id = state.get("user_id", "anonymous")

        if not messages:
            return state

        last_message = messages[-1].content
        ticket_info = await self.analyze_request(last_message)

        result = await self.handle_ecommerce_action(ticket_info, user_id)

        return {
            **state,
            "sub_results": {
                **state.get("sub_results", {}),
                "ticket_handler": result,
            },
        }
