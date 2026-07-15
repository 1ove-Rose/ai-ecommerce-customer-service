"""电商客服 API / MCP 共享数据结构。"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict


class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    category: str
    description: str
    price: Decimal
    stock: int
    attributes: dict[str, Any]


class OrderItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    product_id: str
    product_name: str
    quantity: int
    unit_price: Decimal


class ShipmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    order_id: str
    carrier: str
    tracking_no: str
    status: str
    eta: str | None
    events: list[dict[str, Any]]


class OrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    status: str
    total_amount: Decimal
    payment_status: str
    receiver_name: str
    receiver_phone: str
    receiver_address: str
    extra: dict[str, Any]
    items: list[OrderItemRead] = []
    shipment: ShipmentRead | None = None


class UserProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    phone: str | None
    email: str | None
    member_level: str
    risk_flags: dict[str, Any]


class TicketCreate(BaseModel):
    user_id: str
    order_id: str | None = None
    type: str = "general"
    priority: str = "medium"
    summary: str
    details: str


class TicketRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    order_id: str | None
    type: str
    priority: str
    status: str
    summary: str
    details: str
    events: list[dict[str, Any]]
    created_at: datetime
    updated_at: datetime


class AfterSaleCreate(BaseModel):
    user_id: str
    order_id: str
    type: str
    reason: str


class AfterSaleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    order_id: str
    user_id: str
    type: str
    status: str
    reason: str
    result: str | None
    timeline: list[dict[str, Any]]
    created_at: datetime
    updated_at: datetime


class KnowledgeDocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    source: str
    content: str
    tags: list[str]


class ToolCallLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tool_name: str
    success: bool
    arguments: dict[str, Any]
    result: dict[str, Any] | list[Any] | str | None
    error: str | None
    duration_ms: float
    created_at: datetime