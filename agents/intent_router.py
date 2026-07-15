"""
意图路由 Agent — 电商客服意图识别与分类
负责识别用户消息中的电商业务意图，并为 Supervisor 提供稳定的业务路由建议。
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from tracing.otel_config import trace_agent_call


class IntentCategory(str, Enum):
    """电商客服意图分类"""
    GREETING = "greeting"
    PRODUCT_INQUIRY = "product_inquiry"
    POLICY_FAQ = "policy_faq"
    ORDER_QUERY = "order_query"
    LOGISTICS_QUERY = "logistics_query"
    REFUND_REQUEST = "refund_request"
    RETURN_EXCHANGE = "return_exchange"
    COMPLAINT = "complaint"
    HUMAN_HANDOFF = "human_handoff"
    UNKNOWN = "unknown"


@dataclass
class IntentResult:
    """意图识别结果"""
    primary_intent: IntentCategory
    secondary_intent: str
    confidence: float
    entities: dict[str, str]
    suggested_agent: str


IDENTITY_MESSAGES = {
    "你是谁", "你是什么", "你是啥", "介绍一下你自己", "你能做什么", "你会什么",
    "who are you", "what can you do",
}

GREETING_MESSAGES = {
    "你好", "您好", "在吗", "哈喽", "hello", "hi", "hey", "您好呀", "你好呀",
}


def normalize_smalltalk_message(message: str) -> str:
    return message.strip().lower().strip("。！？!?~～,.， ")


def get_smalltalk_type(message: str) -> str | None:
    """识别不需要业务检索的轻量对话类型。"""
    normalized = normalize_smalltalk_message(message)
    if normalized in IDENTITY_MESSAGES:
        return "identity"
    if normalized in GREETING_MESSAGES or normalized in {"早上好", "下午好", "晚上好"}:
        return "greeting"
    return None


def is_greeting_message(message: str) -> bool:
    """兼容旧调用：识别是否属于轻量对话。"""
    return get_smalltalk_type(message) is not None


def build_smalltalk_response(smalltalk_type: str) -> str:
    if smalltalk_type == "identity":
        return (
            "我是电商客服多 Agent 系统的客服助手，可以帮您处理商品咨询、"
            "订单状态、物流查询、售后申请、发票开具和转人工等问题。"
        )
    return (
        "您好！请问有什么可以帮您的？"
        "您可以咨询商品信息、订单状态、物流查询、售后申请或发票开具等问题。"
    )


def build_greeting_response() -> str:
    return build_smalltalk_response("greeting")


INTENT_SYSTEM_PROMPT = """你是一个专业的电商客服意图识别 Agent。

请从以下维度分析用户消息：
1. primary_intent: 电商一级意图，只能取以下值之一：
   - greeting: 问候、寒暄、打招呼，例如你好、您好、在吗、hello
   - product_inquiry: 商品咨询、规格、价格、库存、保修
   - policy_faq: 退换货政策、发票、会员规则、物流时效、平台规则
   - order_query: 查询订单状态、订单明细、支付状态
   - logistics_query: 查询物流轨迹、配送进度、签收异常
   - refund_request: 申请退款、退款进度
   - return_exchange: 退货、换货、维修
   - complaint: 投诉、纠纷、差评、赔偿诉求
   - human_handoff: 明确要求转人工
   - unknown: 无法判断
2. secondary_intent: 更具体的业务子类型
3. confidence: 0.0-1.0
4. entities: 提取订单号、商品名、SKU、物流单号、售后单号、金额等关键实体
5. suggested_agent: 只能返回 smalltalk、knowledge_rag 或 ticket_handler

路由规则：
- greeting → smalltalk
- product_inquiry、policy_faq、unknown → knowledge_rag
- order_query、logistics_query、refund_request、return_exchange、complaint、human_handoff → ticket_handler

只返回 JSON，不要 Markdown，不要解释。示例：
{
    "primary_intent": "order_query",
    "secondary_intent": "order_status",
    "confidence": 0.92,
    "entities": {"order_id": "10001"},
    "suggested_agent": "ticket_handler"
}
"""


class IntentRouterAgent:
    """意图路由Agent"""

    def __init__(self, llm: ChatOpenAI):
        self.llm = llm

    @trace_agent_call("intent_router")
    async def classify(self, user_message: str) -> IntentResult:
        """对用户消息进行意图分类"""
        smalltalk_type = get_smalltalk_type(user_message)
        if smalltalk_type is not None:
            return IntentResult(
                primary_intent=IntentCategory.GREETING,
                secondary_intent=smalltalk_type,
                confidence=1.0,
                entities={},
                suggested_agent="smalltalk",
            )

        messages = [
            SystemMessage(content=INTENT_SYSTEM_PROMPT),
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
                "primary_intent": "unknown",
                "secondary_intent": "unknown",
                "confidence": 0.0,
                "entities": {},
                "suggested_agent": "knowledge_rag",
            }

        primary_intent = result.get("primary_intent", "unknown")
        if primary_intent not in {item.value for item in IntentCategory}:
            primary_intent = "unknown"

        suggested_agent = result.get("suggested_agent", "knowledge_rag")
        if suggested_agent not in {"smalltalk", "knowledge_rag", "ticket_handler"}:
            suggested_agent = "knowledge_rag"

        return IntentResult(
            primary_intent=IntentCategory(primary_intent),
            secondary_intent=result.get("secondary_intent", "unknown"),
            confidence=result.get("confidence", 0.0),
            entities=result.get("entities", {}),
            suggested_agent=suggested_agent,
        )

    @trace_agent_call("intent_router_process")
    async def process(self, state: dict[str, Any]) -> dict[str, Any]:
        """作为Graph节点处理状态"""
        messages = state.get("messages", [])
        if not messages:
            return state

        last_message = messages[-1].content if messages else ""
        intent_result = await self.classify(last_message)

        next_sub_results = {
            **state.get("sub_results", {}),
            "intent_router": {
                "primary": intent_result.primary_intent.value,
                "secondary": intent_result.secondary_intent,
                "confidence": intent_result.confidence,
                "entities": intent_result.entities,
            },
        }
        if intent_result.suggested_agent == "smalltalk":
            next_sub_results["smalltalk"] = build_smalltalk_response(intent_result.secondary_intent)

        return {
            **state,
            "intent": intent_result.suggested_agent,
            "sub_results": next_sub_results,
        }
