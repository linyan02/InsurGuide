"""
Elasticsearch 客户端

ES 在本项目中为可选组件，可用于存规则、日志或做关键词检索。
若未部署 ES，相关路由可能不可用，但不影响主流程（RAG 用 RAGflow，规则用 ChromaDB）。
"""
from typing import Optional, Dict, List

from elasticsearch import Elasticsearch

from config import settings


class ESClient:
    """
    对 Elasticsearch 的封装：连接、索引文档、搜索、建/删索引、健康检查。
    """

    def __init__(self):
        self.client = None
        self._init_client()

    def _init_client(self):
        """根据配置建立 ES 连接，支持账号密码和 SSL。"""
        try:
            es_config = {"hosts": [f"{settings.ES_HOST}:{settings.ES_PORT}"]}
            if settings.ES_USER and settings.ES_PASSWORD:
                es_config["basic_auth"] = (settings.ES_USER, settings.ES_PASSWORD)
            if settings.ES_USE_SSL:
                es_config["use_ssl"] = True
                es_config["verify_certs"] = True
            self.client = Elasticsearch(**es_config)
            if self.client.ping():
                print(f"✓ Elasticsearch 连接成功: {settings.ES_HOST}:{settings.ES_PORT}")
            else:
                print(f"⚠ Elasticsearch 无法连接: {settings.ES_HOST}:{settings.ES_PORT}")
        except Exception as e:
            print(f"⚠ Elasticsearch 连接失败: {str(e)}")

    def index_document(
        self, index: str, document: Dict, doc_id: Optional[str] = None
    ) -> bool:
        """往指定索引写入一条文档，可指定 id，不指定则自动生成。"""
        if self.client is None:
            raise Exception("Elasticsearch 客户端未初始化")
        try:
            response = self.client.index(index=index, document=document, id=doc_id)
            return response.get("result") in ["created", "updated"]
        except Exception as e:
            print(f"索引文档失败: {str(e)}")
            return False

    def search(
        self, index: str, query: Dict, size: int = 10, from_: int = 0
    ) -> Optional[Dict]:
        """
        在指定索引里按 query 搜索。size 是每页条数，from_ 是跳过条数（分页用）。
        query 是 ES 的 DSL，例如 {"match": {"content": "关键词"}}。
        """
        if self.client is None:
            raise Exception("Elasticsearch 客户端未初始化")
        try:
            return self.client.search(
                index=index, body={"query": query}, size=size, from_=from_
            )
        except Exception as e:
            print(f"搜索失败: {str(e)}")
            return None

    def create_index(
        self,
        index: str,
        mappings: Optional[Dict] = None,
        settings_index: Optional[Dict] = None,
    ) -> bool:
        """创建索引（若已存在则不重复创建）。mappings 定义字段类型，settings 可设分片等。"""
        if self.client is None:
            raise Exception("Elasticsearch 客户端未初始化")
        try:
            if not self.client.indices.exists(index=index):
                self.client.indices.create(
                    index=index,
                    mappings=mappings,
                    settings=settings_index,
                )
            return True
        except Exception as e:
            print(f"创建索引失败: {str(e)}")
            return False

    def delete_index(self, index: str) -> bool:
        """删除整个索引，慎用。"""
        if self.client is None:
            raise Exception("Elasticsearch 客户端未初始化")
        try:
            if self.client.indices.exists(index=index):
                self.client.indices.delete(index=index)
            return True
        except Exception as e:
            print(f"删除索引失败: {str(e)}")
            return False

    def get_health(self) -> Optional[Dict]:
        """获取集群健康状态，运维或健康检查接口用。"""
        if self.client is None:
            raise Exception("Elasticsearch 客户端未初始化")
        try:
            return self.client.cluster.health()
        except Exception as e:
            print(f"获取健康状态失败: {str(e)}")
            return None


_es_client: Optional[ESClient] = None


def get_es_client() -> ESClient:
    """获取 ES 客户端单例，避免重复建连接。"""
    global _es_client
    if _es_client is None:
        _es_client = ESClient()
    return _es_client
