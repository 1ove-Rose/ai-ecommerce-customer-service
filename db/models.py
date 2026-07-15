"""电商客服最小数据域模型。"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import DateTime, ForeignKey, JSON, Numeric, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    phone: Mapped[str | None] = mapped_column(String(32))
    email: Mapped[str | None] = mapped_column(String(255))
    member_level: Mapped[str] = mapped_column(String(32), default="normal")
    risk_flags: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    orders: Mapped[list[Order]] = relationship(back_populates="user")


class Product(TimestampMixin, Base):
    __tablename__ = "products"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    category: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    stock: Mapped[int] = mapped_column(default=0)
    attributes: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class Order(TimestampMixin, Base):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(32))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    payment_status: Mapped[str] = mapped_column(String(32), default="paid")
    receiver_name: Mapped[str] = mapped_column(String(100))
    receiver_phone: Mapped[str] = mapped_column(String(32))
    receiver_address: Mapped[str] = mapped_column(String(500))
    extra: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    user: Mapped[User] = relationship(back_populates="orders")
    items: Mapped[list[OrderItem]] = relationship(back_populates="order", cascade="all, delete-orphan")
    shipment: Mapped[Shipment | None] = relationship(back_populates="order", cascade="all, delete-orphan")


class OrderItem(TimestampMixin, Base):
    __tablename__ = "order_items"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"), index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"), index=True)
    product_name: Mapped[str] = mapped_column(String(255))
    quantity: Mapped[int] = mapped_column(default=1)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))

    order: Mapped[Order] = relationship(back_populates="items")


class Shipment(TimestampMixin, Base):
    __tablename__ = "shipments"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"), unique=True, index=True)
    carrier: Mapped[str] = mapped_column(String(100))
    tracking_no: Mapped[str] = mapped_column(String(100), index=True)
    status: Mapped[str] = mapped_column(String(32))
    eta: Mapped[str | None] = mapped_column(String(100))
    events: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)

    order: Mapped[Order] = relationship(back_populates="shipment")


class AfterSale(TimestampMixin, Base):
    __tablename__ = "after_sales"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    type: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32))
    reason: Mapped[str] = mapped_column(Text)
    result: Mapped[str | None] = mapped_column(Text)
    timeline: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)


class Ticket(TimestampMixin, Base):
    __tablename__ = "tickets"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    order_id: Mapped[str | None] = mapped_column(String(64), index=True)
    type: Mapped[str] = mapped_column(String(32))
    priority: Mapped[str] = mapped_column(String(32), default="medium")
    status: Mapped[str] = mapped_column(String(32), default="created")
    summary: Mapped[str] = mapped_column(String(255))
    details: Mapped[str] = mapped_column(Text)
    events: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)


class ChatSession(TimestampMixin, Base):
    __tablename__ = "chat_sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32), default="active")
    summary: Mapped[str | None] = mapped_column(Text)


class ChatMessage(TimestampMixin, Base):
    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("chat_sessions.id"), index=True)
    role: Mapped[str] = mapped_column(String(32))
    content: Mapped[str] = mapped_column(Text)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)


class KnowledgeDocument(TimestampMixin, Base):
    __tablename__ = "knowledge_documents"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    source: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)


class ToolCallLog(TimestampMixin, Base):
    __tablename__ = "tool_call_logs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tool_name: Mapped[str] = mapped_column(String(100), index=True)
    success: Mapped[bool] = mapped_column(default=True)
    arguments: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    result: Mapped[dict[str, Any] | list[Any] | str | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text)
    duration_ms: Mapped[float] = mapped_column(default=0.0)