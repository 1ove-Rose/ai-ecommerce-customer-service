"""
MCP 工具协议服务端 — 电商客服工具层。

Agent 只通过这里访问订单、物流、售后、工单、知识库和用户画像能力。
工具内部再调用 Service/Repository，避免 Agent 直接访问数据库。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Awaitable, Callable

from pydantic import BaseModel


@dataclass
class ToolDefinition:
    """MCP 工具定义"""

    name: str
    description: str
    input_schema: dict[str, Any]
    handler: Callable[..., Awaitable[Any]]
    category: str = "general"
    requires_auth: bool = False


@dataclass
class ToolCallResult:
    """工具调用结果"""

    tool_name: str
    success: bool
    result: Any = None
    error: str | None = None
    duration_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class MCPToolServer:
    """轻量 MCP 工具服务端。"""

    def __init__(self):
        self._tools: dict[str, ToolDefinition] = {}
        self._call_log: list[ToolCallResult] = []

    def register_tool(self, tool: ToolDefinition) -> None:
        self._tools[tool.name] = tool

    def register(
        self,
        name: str,
        description: str,
        input_schema: dict[str, Any],
        category: str = "general",
        requires_auth: bool = False,
    ) -> Callable:
        """工具注册装饰器"""

        def decorator(func: Callable[..., Awaitable[Any]]) -> Callable:
            self._tools[name] = ToolDefinition(
                name=name,
                description=description,
                input_schema=input_schema,
                handler=func,
                category=category,
                requires_auth=requires_auth,
            )
            return func

        return decorator

    def list_tools(self, category: str | None = None) -> list[dict]:
        tools = []
        for tool in self._tools.values():
            if category and tool.category != category:
                continue
            tools.append(
                {
                    "name": tool.name,
                    "description": tool.description,
                    "inputSchema": tool.input_schema,
                    "category": tool.category,
                }
            )
        return tools

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> ToolCallResult:
        """调用指定工具，并尽力写入数据库审计日志。"""
        import time

        tool = self._tools.get(name)
        if tool is None:
            result = ToolCallResult(
                tool_name=name,
                success=False,
                error=f"Tool '{name}' not found. Available: {list(self._tools.keys())}",
            )
            self._call_log.append(result)
            await _record_tool_call(name, False, arguments, None, result.error, 0.0)
            return result

        start = time.time()
        try:
            output = await tool.handler(**arguments)
            duration_ms = (time.time() - start) * 1000
            result = ToolCallResult(
                tool_name=name,
                success=True,
                result=output,
                duration_ms=duration_ms,
            )
        except Exception as e:
            duration_ms = (time.time() - start) * 1000
            result = ToolCallResult(
                tool_name=name,
                success=False,
                error=str(e),
                duration_ms=duration_ms,
            )

        self._call_log.append(result)
        await _record_tool_call(
            name,
            result.success,
            arguments,
            result.result,
            result.error,
            result.duration_ms,
        )
        return result

    async def handle_jsonrpc(self, request: dict) -> dict:
        method = request.get("method", "")
        params = request.get("params", {})
        req_id = request.get("id", 1)

        try:
            if method == "tools/list":
                result = self.list_tools(category=params.get("category"))
            elif method == "tools/call":
                call_result = await self.call_tool(
                    name=params.get("name", ""),
                    arguments=params.get("arguments", {}),
                )
                result = {
                    "success": call_result.success,
                    "result": call_result.result,
                    "error": call_result.error,
                }
            elif method == "ping":
                result = {"status": "ok"}
            else:
                return {
                    "jsonrpc": "2.0",
                    "error": {"code": -32601, "message": f"Method not found: {method}"},
                    "id": req_id,
                }

            return {"jsonrpc": "2.0", "result": result, "id": req_id}
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32603, "message": str(e)},
                "id": req_id,
            }

    def get_call_log(self, last_n: int = 100) -> list[dict]:
        return [
            {
                "tool": r.tool_name,
                "success": r.success,
                "duration_ms": r.duration_ms,
                "timestamp": r.timestamp,
                "error": r.error,
            }
            for r in self._call_log[-last_n:]
        ]


def _jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    return value


async def _with_service(action: Callable[[Any], Awaitable[Any]]) -> Any:
    from db.session import AsyncSessionLocal
    from services.ecommerce import EcommerceService

    async with AsyncSessionLocal() as session:
        service = EcommerceService(session)
        result = await action(service)
        await session.commit()
        return result


async def _record_tool_call(
    tool_name: str,
    success: bool,
    arguments: dict[str, Any],
    result: Any,
    error: str | None,
    duration_ms: float,
) -> None:
    try:
        from db.session import AsyncSessionLocal
        from repositories.ecommerce import EcommerceRepository

        async with AsyncSessionLocal() as session:
            repo = EcommerceRepository(session)
            await repo.record_tool_call(
                tool_name=tool_name,
                success=success,
                arguments=_jsonable(arguments),
                result=_jsonable(result),
                error=error,
                duration_ms=duration_ms,
            )
            await session.commit()
    except Exception:
        # 数据库未启动时，MCP 仍保留内存调用日志，避免工具层拖垮主流程。
        return


def create_default_tools(server: MCPToolServer) -> MCPToolServer:
    """注册电商客服默认 MCP 工具集。"""

    @server.register(
        name="order_query",
        description="查询订单详情，包括订单状态、支付状态、商品明细和物流摘要",
        input_schema={
            "type": "object",
            "properties": {
                "order_id": {"type": "string", "description": "订单号"},
            },
            "required": ["order_id"],
        },
        category="order",
    )
    async def order_query(order_id: str) -> dict:
        from schemas.ecommerce import OrderRead

        async def action(service):
            order = await service.get_order_detail(order_id)
            if order is None:
                return {"found": False, "message": f"未找到订单 {order_id}"}
            return {"found": True, "order": OrderRead.model_validate(order).model_dump(mode="json")}

        return await _with_service(action)

    @server.register(
        name="order_list_by_user",
        description="查询用户订单列表",
        input_schema={
            "type": "object",
            "properties": {
                "user_id": {"type": "string", "description": "用户ID"},
            },
            "required": ["user_id"],
        },
        category="order",
    )
    async def order_list_by_user(user_id: str) -> dict:
        from schemas.ecommerce import OrderRead

        async def action(service):
            orders = await service.list_user_orders(user_id)
            return {
                "user_id": user_id,
                "orders": [OrderRead.model_validate(order).model_dump(mode="json") for order in orders],
            }

        return await _with_service(action)

    @server.register(
        name="logistics_query",
        description="查询订单物流轨迹",
        input_schema={
            "type": "object",
            "properties": {
                "order_id": {"type": "string", "description": "订单号"},
            },
            "required": ["order_id"],
        },
        category="logistics",
    )
    async def logistics_query(order_id: str) -> dict:
        async def action(service):
            order = await service.get_order_detail(order_id)
            if order is None:
                return {"found": False, "message": f"未找到订单 {order_id}"}
            if order.shipment is None:
                return {"found": False, "message": f"订单 {order_id} 暂无物流信息"}
            return {
                "found": True,
                "order_id": order.id,
                "carrier": order.shipment.carrier,
                "tracking_no": order.shipment.tracking_no,
                "status": order.shipment.status,
                "eta": order.shipment.eta,
                "events": order.shipment.events,
            }

        return await _with_service(action)

    @server.register(
        name="after_sale_create",
        description="创建售后申请，支持退款、退货、换货、维修",
        input_schema={
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
                "order_id": {"type": "string"},
                "type": {"type": "string", "enum": ["refund", "return_refund", "exchange", "repair"]},
                "reason": {"type": "string"},
            },
            "required": ["user_id", "order_id", "type", "reason"],
        },
        category="after_sale",
    )
    async def after_sale_create(user_id: str, order_id: str, type: str, reason: str) -> dict:
        from schemas.ecommerce import AfterSaleCreate, AfterSaleRead

        async def action(service):
            after_sale = await service.create_after_sale(
                AfterSaleCreate(user_id=user_id, order_id=order_id, type=type, reason=reason)
            )
            return AfterSaleRead.model_validate(after_sale).model_dump(mode="json")

        return await _with_service(action)

    @server.register(
        name="after_sale_query",
        description="查询售后申请进度",
        input_schema={
            "type": "object",
            "properties": {
                "after_sale_id": {"type": "string", "description": "售后单号"},
            },
            "required": ["after_sale_id"],
        },
        category="after_sale",
    )
    async def after_sale_query(after_sale_id: str) -> dict:
        from schemas.ecommerce import AfterSaleRead

        async def action(service):
            after_sale = await service.get_after_sale(after_sale_id)
            if after_sale is None:
                return {"found": False, "message": f"未找到售后单 {after_sale_id}"}
            return {"found": True, "after_sale": AfterSaleRead.model_validate(after_sale).model_dump(mode="json")}

        return await _with_service(action)

    @server.register(
        name="ticket_create",
        description="创建人工客服工单或投诉工单",
        input_schema={
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
                "order_id": {"type": "string"},
                "type": {"type": "string"},
                "priority": {"type": "string", "enum": ["low", "medium", "high", "urgent"]},
                "summary": {"type": "string"},
                "details": {"type": "string"},
            },
            "required": ["user_id", "summary", "details"],
        },
        category="ticket",
    )
    async def ticket_create(
        user_id: str,
        summary: str,
        details: str,
        order_id: str | None = None,
        type: str = "general",
        priority: str = "medium",
    ) -> dict:
        from schemas.ecommerce import TicketCreate, TicketRead

        async def action(service):
            ticket = await service.create_ticket(
                TicketCreate(
                    user_id=user_id,
                    order_id=order_id,
                    type=type,
                    priority=priority,
                    summary=summary,
                    details=details,
                )
            )
            return TicketRead.model_validate(ticket).model_dump(mode="json")

        return await _with_service(action)

    @server.register(
        name="ticket_update",
        description="更新工单状态",
        input_schema={
            "type": "object",
            "properties": {
                "ticket_id": {"type": "string"},
                "status": {"type": "string"},
                "message": {"type": "string"},
            },
            "required": ["ticket_id", "status"],
        },
        category="ticket",
    )
    async def ticket_update(ticket_id: str, status: str, message: str | None = None) -> dict:
        from schemas.ecommerce import TicketRead

        async def action(service):
            ticket = await service.update_ticket_status(ticket_id, status, message)
            if ticket is None:
                return {"found": False, "message": f"未找到工单 {ticket_id}"}
            return {"found": True, "ticket": TicketRead.model_validate(ticket).model_dump(mode="json")}

        return await _with_service(action)

    @server.register(
        name="knowledge_search",
        description="搜索电商知识库，返回 FAQ、政策或平台规则片段",
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "搜索查询"},
                "top_k": {"type": "integer", "description": "返回数量", "default": 3},
            },
            "required": ["query"],
        },
        category="knowledge",
    )
    async def knowledge_search(query: str, top_k: int = 3) -> list[dict]:
        from schemas.ecommerce import KnowledgeDocumentRead

        async def action(service):
            docs = await service.search_knowledge_documents(query, top_k)
            return [KnowledgeDocumentRead.model_validate(doc).model_dump(mode="json") for doc in docs]

        return await _with_service(action)

    @server.register(
        name="user_profile_query",
        description="查询用户画像、会员等级和风险标签",
        input_schema={
            "type": "object",
            "properties": {
                "user_id": {"type": "string", "description": "用户ID"},
            },
            "required": ["user_id"],
        },
        category="customer",
    )
    async def user_profile_query(user_id: str) -> dict:
        from schemas.ecommerce import UserProfileRead

        async def action(service):
            user = await service.get_user_profile(user_id)
            if user is None:
                return {"found": False, "message": f"未找到用户 {user_id}"}
            return {"found": True, "user": UserProfileRead.model_validate(user).model_dump(mode="json")}

        return await _with_service(action)

    return server