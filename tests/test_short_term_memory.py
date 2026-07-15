from __future__ import annotations

import pytest

from memory.short_term import ShortTermMemory


@pytest.mark.asyncio
async def test_short_term_memory_uses_in_memory_fallback_when_redis_unavailable():
    memory = ShortTermMemory(redis_url="redis://127.0.0.1:1/0", max_turns=2, ttl_seconds=1)

    await memory.add_message("session-a", "user", "第一句")
    await memory.add_message("session-a", "assistant", "第二句")
    await memory.add_message("session-a", "user", "第三句")

    history = await memory.get_history("session-a")

    assert len(history) == 2
    assert history[0]["content"] == "第二句"
    assert history[1]["content"] == "第三句"