"""电商业务服务层。"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from repositories.ecommerce import EcommerceRepository
from schemas.ecommerce import AfterSaleCreate, TicketCreate


class EcommerceService:
    """封装电商客服业务规则，供 API 和 MCP 工具复用。"""

    def __init__(self, session: AsyncSession):
        self.repo = EcommerceRepository(session)

    async def get_user_profile(self, user_id: str):
        return await self.repo.get_user(user_id)

    async def search_products(self, keyword: str | None = None):
        return await self.repo.list_products(keyword)

    async def get_order_detail(self, order_id: str):
        return await self.repo.get_order(order_id)

    async def list_user_orders(self, user_id: str):
        return await self.repo.list_orders_by_user(user_id)

    async def create_ticket(self, payload: TicketCreate):
        return await self.repo.create_ticket(payload)

    async def list_tickets(self, user_id: str | None = None):
        return await self.repo.list_tickets(user_id)

    async def get_ticket(self, ticket_id: str):
        return await self.repo.get_ticket(ticket_id)

    async def create_after_sale(self, payload: AfterSaleCreate):
        order = await self.repo.get_order(payload.order_id)
        if order is None:
            raise ValueError(f"订单不存在: {payload.order_id}")
        if order.user_id != payload.user_id:
            raise ValueError("订单不属于当前用户，不能创建售后申请")
        if order.status not in {"paid", "shipped", "delivered"}:
            raise ValueError(f"当前订单状态不支持售后: {order.status}")
        return await self.repo.create_after_sale(payload)

    async def get_after_sale(self, after_sale_id: str):
        return await self.repo.get_after_sale(after_sale_id)

    async def list_knowledge_documents(self):
        return await self.repo.list_knowledge_documents()

    async def search_knowledge_documents(self, query: str, top_k: int = 3):
        return await self.repo.search_knowledge_documents(query, top_k)

    async def update_ticket_status(self, ticket_id: str, status: str, message: str | None = None):
        return await self.repo.update_ticket_status(ticket_id, status, message)