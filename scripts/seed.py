"""初始化电商客服演示数据。"""

from __future__ import annotations

import asyncio
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from db.models import (  # noqa: E402
    AfterSale,
    ChatSession,
    KnowledgeDocument,
    Order,
    OrderItem,
    Product,
    Shipment,
    Ticket,
    User,
)
from db.session import AsyncSessionLocal, init_db  # noqa: E402


async def seed() -> None:
    await init_db()

    async with AsyncSessionLocal() as session:
        objects = [
            User(
                id="u_1001",
                name="张三",
                phone="13800001111",
                email="zhangsan@example.com",
                member_level="gold",
                risk_flags={"refund_frequency": "normal"},
            ),
            User(
                id="u_1002",
                name="李四",
                phone="13900002222",
                email="lisi@example.com",
                member_level="normal",
                risk_flags={"refund_frequency": "high"},
            ),
            Product(
                id="p_phone_001",
                name="Aurora X1 智能手机",
                category="手机数码",
                description="6.7 英寸 OLED 屏，支持 5G，官方质保一年。",
                price=Decimal("3999.00"),
                stock=42,
                attributes={"color": ["黑色", "银色"], "storage": ["256G", "512G"]},
            ),
            Product(
                id="p_headset_001",
                name="Breeze Pro 降噪耳机",
                category="手机配件",
                description="主动降噪，最长 30 小时续航，支持七天无理由退货。",
                price=Decimal("699.00"),
                stock=120,
                attributes={"color": ["白色", "蓝色"]},
            ),
            Product(
                id="p_keyboard_001",
                name="KeyMaster 机械键盘",
                category="电脑外设",
                description="热插拔机械轴，RGB 背光，两年质保。",
                price=Decimal("499.00"),
                stock=60,
                attributes={"switch": ["茶轴", "红轴"]},
            ),
            Order(
                id="ORD-10001",
                user_id="u_1001",
                status="shipped",
                total_amount=Decimal("3999.00"),
                payment_status="paid",
                receiver_name="张三",
                receiver_phone="13800001111",
                receiver_address="上海市浦东新区示例路 100 号",
                extra={"invoice": "电子普通发票"},
            ),
            OrderItem(
                id="OI-10001-1",
                order_id="ORD-10001",
                product_id="p_phone_001",
                product_name="Aurora X1 智能手机",
                quantity=1,
                unit_price=Decimal("3999.00"),
            ),
            Shipment(
                id="SHP-10001",
                order_id="ORD-10001",
                carrier="顺丰速运",
                tracking_no="SF100010001CN",
                status="in_transit",
                eta="预计明日 18:00 前送达",
                events=[
                    {"time": "2026-07-14 09:30", "message": "包裹已揽收"},
                    {"time": "2026-07-15 08:10", "message": "运输中，已到达上海分拨中心"},
                ],
            ),
            Order(
                id="ORD-10002",
                user_id="u_1002",
                status="delivered",
                total_amount=Decimal("699.00"),
                payment_status="paid",
                receiver_name="李四",
                receiver_phone="13900002222",
                receiver_address="杭州市西湖区示例街 88 号",
                extra={"invoice": "未申请"},
            ),
            OrderItem(
                id="OI-10002-1",
                order_id="ORD-10002",
                product_id="p_headset_001",
                product_name="Breeze Pro 降噪耳机",
                quantity=1,
                unit_price=Decimal("699.00"),
            ),
            Shipment(
                id="SHP-10002",
                order_id="ORD-10002",
                carrier="京东物流",
                tracking_no="JD100020002CN",
                status="delivered",
                eta=None,
                events=[
                    {"time": "2026-07-12 10:00", "message": "包裹已揽收"},
                    {"time": "2026-07-13 16:20", "message": "用户本人已签收"},
                ],
            ),
            AfterSale(
                id="AS-10002",
                order_id="ORD-10002",
                user_id="u_1002",
                type="return_refund",
                status="reviewing",
                reason="耳机佩戴不适，申请七天无理由退货",
                result=None,
                timeline=[
                    {"time": "2026-07-14 12:00", "message": "售后申请已提交"},
                    {"time": "2026-07-14 14:00", "message": "等待客服审核"},
                ],
            ),
            Ticket(
                id="TK-10001",
                user_id="u_1002",
                order_id="ORD-10002",
                type="return_exchange",
                priority="medium",
                status="processing",
                summary="退货退款审核中",
                details="用户申请七天无理由退货，等待客服审核。",
                events=[{"time": "2026-07-14 14:00", "message": "工单进入处理中"}],
            ),
            ChatSession(
                id="demo-session-1001",
                user_id="u_1001",
                status="active",
                summary="演示会话：查询订单和物流",
            ),
            KnowledgeDocument(
                id="kb-refund-policy",
                title="退换货政策",
                source="seed/refund_policy.md",
                content="支持七天无理由退货。商品需保持完好，不影响二次销售。部分特殊商品以页面规则为准。",
                tags=["售后", "退款", "退货"],
            ),
            KnowledgeDocument(
                id="kb-shipping-policy",
                title="物流时效说明",
                source="seed/shipping_policy.md",
                content="普通商品通常 24 小时内发货，偏远地区配送时效可能延长。具体到达时间以物流轨迹为准。",
                tags=["物流", "配送"],
            ),
            KnowledgeDocument(
                id="kb-invoice-policy",
                title="发票规则",
                source="seed/invoice_policy.md",
                content="订单完成支付后可申请电子普通发票。企业发票需填写完整抬头和税号。",
                tags=["发票", "订单"],
            ),
        ]

        for obj in objects:
            await session.merge(obj)

        await session.commit()

    print("电商客服演示数据已初始化。")


if __name__ == "__main__":
    asyncio.run(seed())