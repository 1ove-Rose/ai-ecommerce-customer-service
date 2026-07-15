"""
数据库连接与会话管理。

Agent 不直接依赖这里；MCP 工具应通过 service/repository 访问数据库。
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://app:app@localhost:5432/smartcs",
)

engine = create_async_engine(DATABASE_URL, echo=os.getenv("SQL_ECHO", "false").lower() == "true")
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session


async def init_db() -> None:
    from db.models import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)