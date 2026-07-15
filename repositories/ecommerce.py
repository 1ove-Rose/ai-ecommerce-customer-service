"""电商数据访问层。"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db.models import (
    AfterSale,
    KnowledgeDocument,
    Order,
    Product,
    Ticket,
    ToolCallLog,
    User,
)
from schemas.ecommerce import AfterSaleCreate, TicketCreate


class EcommerceRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_user(self, user_id: str) -> User | None:
        return await self.session.get(User, user_id)

    async def list_products(self, keyword: str | None = None) -> list[Product]:
        stmt = select(Product).order_by(Product.created_at.desc())
        if keyword:
            stmt = stmt.where(Product.name.contains(keyword))
        result = await self.session.scalars(stmt)
        return list(result)

    async def get_order(self, order_id: str) -> Order | None:
        stmt = (
            select(Order)
            .where(Order.id == order_id)
            .options(selectinload(Order.items), selectinload(Order.shipment))
        )
        return await self.session.scalar(stmt)

    async def list_orders_by_user(self, user_id: str) -> list[Order]:
        stmt = (
            select(Order)
            .where(Order.user_id == user_id)
            .order_by(Order.created_at.desc())
            .options(selectinload(Order.items), selectinload(Order.shipment))
        )
        result = await self.session.scalars(stmt)
        return list(result)

    async def list_tickets(self, user_id: str | None = None) -> list[Ticket]:
        stmt = select(Ticket).order_by(Ticket.created_at.desc())
        if user_id:
            stmt = stmt.where(Ticket.user_id == user_id)
        result = await self.session.scalars(stmt)
        return list(result)

    async def get_ticket(self, ticket_id: str) -> Ticket | None:
        return await self.session.get(Ticket, ticket_id)

    async def create_ticket(self, payload: TicketCreate) -> Ticket:
        ticket = Ticket(
            id=f"TK-{uuid.uuid4().hex[:8].upper()}",
            user_id=payload.user_id,
            order_id=payload.order_id,
            type=payload.type,
            priority=payload.priority,
            status="created",
            summary=payload.summary,
            details=payload.details,
            events=[{"status": "created", "message": "工单已创建"}],
        )
        self.session.add(ticket)
        await self.session.flush()
        return ticket

    async def create_after_sale(self, payload: AfterSaleCreate) -> AfterSale:
        after_sale = AfterSale(
            id=f"AS-{uuid.uuid4().hex[:8].upper()}",
            user_id=payload.user_id,
            order_id=payload.order_id,
            type=payload.type,
            status="created",
            reason=payload.reason,
            result=None,
            timeline=[{"status": "created", "message": "售后申请已创建"}],
        )
        self.session.add(after_sale)
        await self.session.flush()
        return after_sale

    async def get_after_sale(self, after_sale_id: str) -> AfterSale | None:
        return await self.session.get(AfterSale, after_sale_id)

    async def list_knowledge_documents(self) -> list[KnowledgeDocument]:
        result = await self.session.scalars(select(KnowledgeDocument).order_by(KnowledgeDocument.created_at.desc()))
        return list(result)

    async def search_knowledge_documents(self, query: str, top_k: int = 3) -> list[KnowledgeDocument]:
        stmt = (
            select(KnowledgeDocument)
            .where(KnowledgeDocument.content.contains(query) | KnowledgeDocument.title.contains(query))
            .order_by(KnowledgeDocument.created_at.desc())
            .limit(top_k)
        )
        result = await self.session.scalars(stmt)
        return list(result)

    async def update_ticket_status(self, ticket_id: str, status: str, message: str | None = None) -> Ticket | None:
        ticket = await self.get_ticket(ticket_id)
        if ticket is None:
            return None
        ticket.status = status
        events = list(ticket.events or [])
        events.append({"status": status, "message": message or f"工单状态更新为 {status}"})
        ticket.events = events
        await self.session.flush()
        return ticket

    async def record_tool_call(
        self,
        tool_name: str,
        success: bool,
        arguments: dict[str, Any],
        result: dict[str, Any] | list[Any] | str | None = None,
        error: str | None = None,
        duration_ms: float = 0.0,
    ) -> ToolCallLog:
        log = ToolCallLog(
            id=f"LOG-{uuid.uuid4().hex[:10].upper()}",
            tool_name=tool_name,
            success=success,
            arguments=arguments,
            result=result,
            error=error,
            duration_ms=duration_ms,
        )
        self.session.add(log)
        await self.session.flush()
        return log