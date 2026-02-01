"""
向量数据库连接模块
支持 ChromaDB 和 FAISS
"""
import os
from typing import List, Optional
import chromadb
from chromadb.config import Settings as ChromaSettings
from config import settings


class VectorDB:
    """向量数据库客户端"""
    
    def __init__(self):
        """初始化向量数据库连接"""
        self.client = None
        self.collection = None
        self._init_chromadb()
    
    def _init_chromadb(self):
        """初始化 ChromaDB"""
        try:
            # 确保目录存在
            os.makedirs(settings.VECTOR_DB_PATH, exist_ok=True)
            
            # 创建 ChromaDB 客户端
            self.client = chromadb.PersistentClient(
                path=settings.VECTOR_DB_PATH,
                settings=ChromaSettings(
                    anonymized_telemetry=False
                )
            )
            
            # 获取或创建集合
            self.collection = self.client.get_or_create_collection(
                name=settings.VECTOR_DB_COLLECTION,
                metadata={"description": "InsurGuide vector collection"}
            )
            print(f"✓ ChromaDB 连接成功: {settings.VECTOR_DB_PATH}")
        except Exception as e:
            print(f"⚠ ChromaDB 连接失败: {str(e)}")
            print("提示: 向量数据库功能将不可用，但应用仍可启动")
    
    def add_documents(
        self,
        documents: List[str],
        embeddings: Optional[List[List[float]]] = None,
        metadatas: Optional[List[dict]] = None,
        ids: Optional[List[str]] = None
    ):
        """添加文档到向量数据库"""
        if self.collection is None:
            raise Exception("向量数据库未初始化")
        
        try:
            if embeddings is None:
                # 如果没有提供 embeddings，ChromaDB 会自动生成
                self.collection.add(
                    documents=documents,
                    metadatas=metadatas or [{}] * len(documents),
                    ids=ids or [f"doc_{i}" for i in range(len(documents))]
                )
            else:
                self.collection.add(
                    embeddings=embeddings,
                    documents=documents,
                    metadatas=metadatas or [{}] * len(documents),
                    ids=ids or [f"doc_{i}" for i in range(len(documents))]
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
        where: Optional[dict] = None
    ):
        """查询向量数据库"""
        if self.collection is None:
            raise Exception("向量数据库未初始化")
        
        try:
            results = self.collection.query(
                query_texts=query_texts,
                query_embeddings=query_embeddings,
                n_results=n_results,
                where=where
            )
            return results
        except Exception as e:
            print(f"查询失败: {str(e)}")
            return None
    
    def delete(self, ids: Optional[List[str]] = None, where: Optional[dict] = None):
        """删除向量数据库中的文档"""
        if self.collection is None:
            raise Exception("向量数据库未初始化")
        
        try:
            self.collection.delete(ids=ids, where=where)
            return True
        except Exception as e:
            print(f"删除失败: {str(e)}")
            return False


# 全局向量数据库实例
vector_db = VectorDB()
