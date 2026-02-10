"""
增强 RAG 服务层单元测试：融合、精排（纯函数，无外部依赖）
"""
import pytest

from services.rag.fusion import fusion
from services.rag.rerank import rerank


def test_fusion_empty():
    out = fusion([])
    assert out["documents"] == []
    assert out["metadatas"] == []


def test_fusion_dedup():
    results = [
        {"content": "重复内容", "source": "A", "score": 0.9, "origin": "ragflow"},
        {"content": "重复内容", "source": "B", "score": 0.8, "origin": "local"},
        {"content": "另一段", "source": "C", "score": 0.7, "origin": "ragflow"},
    ]
    out = fusion(results)
    assert len(out["documents"]) == 2
    assert out["documents"][0] == "重复内容"
    assert out["documents"][1] == "另一段"
    assert len(out["metadatas"]) == 2


def test_rerank_passthrough_on_error():
    out = rerank({"error": "某错误"})
    assert "error" in out


def test_rerank_sort_and_cut():
    fused = {
        "documents": ["d1", "d2", "d3", "d4"],
        "metadatas": [
            {"source": "a", "score": 0.5},
            {"source": "b", "score": 0.9},
            {"source": "c", "score": 0.7},
            {"source": "d", "score": 0.8},
        ],
    }
    out = rerank(fused, top_k=2)
    assert len(out["documents"]) == 2
    assert out["documents"][0] == "d2"  # score 0.9
    assert out["documents"][1] == "d4"  # score 0.8
    assert out["metadatas"][0]["score"] == 0.9
