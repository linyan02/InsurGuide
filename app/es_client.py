"""
Elasticsearch 客户端模块
"""
from elasticsearch import Elasticsearch
from config import settings
from typing import Optional, Dict, List


class ESClient:
    """Elasticsearch 客户端"""
    
    def __init__(self):
        """初始化 Elasticsearch 连接"""
        self.client = None
        self._init_client()
    
    def _init_client(self):
        """初始化 Elasticsearch 客户端"""
        try:
            es_config = {
                "hosts": [f"{settings.ES_HOST}:{settings.ES_PORT}"],
            }
            
            if settings.ES_USER and settings.ES_PASSWORD:
                es_config["basic_auth"] = (settings.ES_USER, settings.ES_PASSWORD)
            
            if settings.ES_USE_SSL:
                es_config["use_ssl"] = True
                es_config["verify_certs"] = True
            
            self.client = Elasticsearch(**es_config)
            
            # 测试连接
            if self.client.ping():
                print(f"✓ Elasticsearch 连接成功: {settings.ES_HOST}:{settings.ES_PORT}")
            else:
                print(f"⚠ Elasticsearch 无法连接: {settings.ES_HOST}:{settings.ES_PORT}")
                print("提示: Elasticsearch 功能将不可用，但应用仍可启动")
        except Exception as e:
            print(f"⚠ Elasticsearch 连接失败: {str(e)}")
            print("提示: Elasticsearch 功能将不可用，但应用仍可启动")
    
    def index_document(
        self,
        index: str,
        document: Dict,
        doc_id: Optional[str] = None
    ) -> bool:
        """索引文档到 Elasticsearch"""
        if self.client is None:
            raise Exception("Elasticsearch 客户端未初始化")
        try:
            response = self.client.index(
                index=index,
                document=document,
                id=doc_id
            )
            return response.get("result") in ["created", "updated"]
        except Exception as e:
            print(f"索引文档失败: {str(e)}")
            return False
    
    def search(
        self,
        index: str,
        query: Dict,
        size: int = 10,
        from_: int = 0
    ) -> Optional[Dict]:
        """搜索文档"""
        if self.client is None:
            raise Exception("Elasticsearch 客户端未初始化")
        try:
            response = self.client.search(
                index=index,
                body={"query": query},
                size=size,
                from_=from_
            )
            return response
        except Exception as e:
            print(f"搜索失败: {str(e)}")
            return None
    
    def create_index(
        self,
        index: str,
        mappings: Optional[Dict] = None,
        settings: Optional[Dict] = None
    ) -> bool:
        """创建索引"""
        if self.client is None:
            raise Exception("Elasticsearch 客户端未初始化")
        try:
            if not self.client.indices.exists(index=index):
                self.client.indices.create(
                    index=index,
                    mappings=mappings,
                    settings=settings
                )
                print(f"✓ 索引创建成功: {index}")
            return True
        except Exception as e:
            print(f"创建索引失败: {str(e)}")
            return False
    
    def delete_index(self, index: str) -> bool:
        """删除索引"""
        if self.client is None:
            raise Exception("Elasticsearch 客户端未初始化")
        try:
            if self.client.indices.exists(index=index):
                self.client.indices.delete(index=index)
                print(f"✓ 索引删除成功: {index}")
            return True
        except Exception as e:
            print(f"删除索引失败: {str(e)}")
            return False
    
    def get_health(self) -> Optional[Dict]:
        """获取集群健康状态"""
        if self.client is None:
            raise Exception("Elasticsearch 客户端未初始化")
        try:
            return self.client.cluster.health()
        except Exception as e:
            print(f"获取健康状态失败: {str(e)}")
            return None


# 全局 ES 客户端实例（延迟初始化，避免启动时连接失败）
es_client = None

def get_es_client():
    """获取 ES 客户端（延迟初始化）"""
    global es_client
    if es_client is None:
        es_client = ESClient()
    return es_client
