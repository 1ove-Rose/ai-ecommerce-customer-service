from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

from memory.long_term import LongTermMemory


def make_work_dir() -> Path:
    path = Path(".pytest_tmp") / uuid4().hex
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_long_term_memory_loads_local_knowledge_base():
    work_dir = make_work_dir()
    try:
        kb_dir = work_dir / "knowledge_base"
        kb_dir.mkdir()
        (kb_dir / "policy.md").write_text(
            "七天无理由退货需要保持商品、配件和包装完整。退款通常 3 到 5 个工作日到账。",
            encoding="utf-8",
        )

        memory = LongTermMemory(
            index_path=str(work_dir / "faiss_index"),
            embedding_backend="hash",
            embedding_dim=256,
        )

        loaded = memory.load_knowledge_base(str(kb_dir))
        results = memory.search("七天无理由退货 包装完整", top_k=1)

        assert loaded >= 1
        assert results
        assert "七天无理由退货" in results[0]["content"]
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


def test_long_term_memory_falls_back_without_faiss():
    work_dir = make_work_dir()
    try:
        memory = LongTermMemory(
            index_path=str(work_dir / "faiss_index"),
            embedding_backend="hash",
            embedding_dim=128,
        )
        memory._index = None
        memory.add_document("物流超过 48 小时未更新应创建人工工单。", source="logistics.md")

        results = memory.search("物流 48 小时", top_k=1)

        assert len(results) == 1
        assert results[0]["source"] == "logistics.md"
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
