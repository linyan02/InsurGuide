"""
向量数据库 - ChromaDB

本项目的「知识库检索」用的是 RAGflow，ChromaDB 这里主要用来存：
- 意图规则（intent_rules 集合）：问题样例 + 对应意图，用于 rule/llm_vector 模式
- 改写规则（rewrite_rules 集合）：原问 + 改写问，用于问题改写
数据存在本机目录 VECTOR_DB_PATH，不用单独起服务。
"""
import os
from typing import List, Optional

import chromadb
from chromadb.config import Settings as ChromaSettings

from config import settings


class VectorDB:
    """
    对 ChromaDB 的封装。启动时连上默认集合，也支持按名字拿别的集合（意图/改写规则等）。
    """

    def __init__(self):
        self.client = None   # ChromaDB 客户端
        self.collection = None  # 默认集合，大部分逻辑会用「按名取集合」不用这个
        self._init_chromadb()

    def _init_chromadb(self):
        """初始化 ChromaDB：创建目录、建持久化客户端、拿到默认集合。"""
        try:
            os.makedirs(settings.VECTOR_DB_PATH, exist_ok=True)
            self.client = chromadb.PersistentClient(
                path=settings.VECTOR_DB_PATH,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            self.collection = self.client.get_or_create_collection(
                name=settings.VECTOR_DB_COLLECTION,
                metadata={"description": "InsurGuide vector collection"},
            )
            print(f"✓ ChromaDB 连接成功: {settings.VECTOR_DB_PATH}")
        except Exception as e:
            print(f"⚠ ChromaDB 连接失败: {str(e)}")

    def add_documents(
        self,
        documents: List[str],
        embeddings: Optional[List[List[float]]] = None,
        metadatas: Optional[List[dict]] = None,
        ids: Optional[List[str]] = None,
    ):
        """
        向默认集合里添加文档。可只传文本（Chroma 会自己算向量），或自己传 embeddings。
        metadatas/ids 可选，不传会生成默认 id。
        """
        if self.collection is None:
            raise Exception("向量数据库未初始化")
        try:
            meta = metadatas or [{}] * len(documents)
            id_list = ids or [f"doc_{i}" for i in range(len(documents))]
            if embeddings is None:
                self.collection.add(documents=documents, metadatas=meta, ids=id_list)
            else:
                self.collection.add(
                    embeddings=embeddings, documents=documents, metadatas=meta, ids=id_list
                )
            return True
        except Exception as e:
            print(f"添加文档失败: {str(e)}")
            return False

    def query(
        self,
        query_texts: Optional[List[str]] = None,
        query_embeddings: Optional[List[List[float]]] = None,
        n_results: int = 5,
        where: Optional[dict] = None,
    ):
        """
        在默认集合里做相似度检索。可传 query_texts（会内部转向量）或 query_embeddings。
        where 是元数据过滤条件。
        """
        if self.collection is None:
            raise Exception("向量数据库未初始化")
        try:
            return self.collection.query(
                query_texts=query_texts,
                query_embeddings=query_embeddings,
                n_results=n_results,
                where=where,
            )
        except Exception as e:
            print(f"查询失败: {str(e)}")
            return None

    def delete(self, ids: Optional[List[str]] = None, where: Optional[dict] = None):
        """按 id 或按条件删除默认集合里的文档。"""
        if self.collection is None:
            raise Exception("向量数据库未初始化")
        try:
            self.collection.delete(ids=ids, where=where)
            return True
        except Exception as e:
            print(f"删除失败: {str(e)}")
            return False

    def get_collection(self, name: str):
        """
        按名字拿到一个集合（不存在会创建）。意图规则、改写规则都用不同集合名。
        """
        if self.client is None:
            return None
        try:
            return self.client.get_or_create_collection(
                name=name, metadata={"description": f"Collection: {name}"}
            )
        except Exception as e:
            print(f"获取集合 {name} 失败: {e}")
            return None

    def query_collection(
        self,
        collection_name: str,
        query_texts: Optional[List[str]] = None,
        n_results: int = 5,
        where: Optional[dict] = None,
    ):
        """
        在指定集合里做相似度检索。意图/改写模块会调这个，传入 intent_rules 或 rewrite_rules。
        """
        coll = self.get_collection(collection_name)
        if coll is None:
            return None
        try:
            return coll.query(
                query_texts=query_texts, n_results=n_results, where=where
            )
        except Exception as e:
            print(f"查询集合 {collection_name} 失败: {e}")
            return None

    def add_to_collection(
        self,
        collection_name: str,
        documents: List[str],
        metadatas: Optional[List[dict]] = None,
        ids: Optional[List[str]] = None,
    ) -> bool:
        """向指定集合添加文档，用于导入意图规则或改写规则。"""
        coll = self.get_collection(collection_name)
        if coll is None:
            return False
        try:
            coll.add(
                documents=documents,
                metadatas=metadatas or [{}] * len(documents),
                ids=ids or [f"doc_{i}" for i in range(len(documents))],
            )
            return True
        except Exception as e:
            print(f"向集合 {collection_name} 添加文档失败: {e}")
            return False


# 全局单例，别处 from core.vector_db import vector_db 用这个即可
vector_db = VectorDB()
