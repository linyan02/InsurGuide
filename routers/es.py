"""
Elasticsearch 路由
"""
from typing import Dict, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.es_client import get_es_client
from app.auth import get_current_active_user
from models.user import User

router = APIRouter(prefix="/api/es", tags=["Elasticsearch"])


class IndexDocument(BaseModel):
    """索引文档模型"""
    index: str
    document: Dict
    doc_id: Optional[str] = None


class SearchQuery(BaseModel):
    """搜索查询模型"""
    index: str
    query: Dict
    size: int = 10
    from_: int = 0


class CreateIndex(BaseModel):
    """创建索引模型"""
    index: str
    mappings: Optional[Dict] = None
    settings: Optional[Dict] = None


@router.post("/index")
def index_document(
    index_data: IndexDocument,
    current_user: User = Depends(get_current_active_user)
):
    """索引文档到 Elasticsearch"""
    try:
        es_client = get_es_client()
        result = es_client.index_document(
            index=index_data.index,
            document=index_data.document,
            doc_id=index_data.doc_id
        )
        if result:
            return {"message": "文档索引成功"}
        else:
            raise HTTPException(status_code=500, detail="文档索引失败")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search")
def search_documents(
    search_data: SearchQuery,
    current_user: User = Depends(get_current_active_user)
):
    """搜索文档"""
    try:
        es_client = get_es_client()
        results = es_client.search(
            index=search_data.index,
            query=search_data.query,
            size=search_data.size,
            from_=search_data.from_
        )
        if results:
            return {"results": results}
        else:
            raise HTTPException(status_code=500, detail="搜索失败")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/create-index")
def create_index(
    index_data: CreateIndex,
    current_user: User = Depends(get_current_active_user)
):
    """创建索引"""
    try:
        result = es_client.create_index(
            index=index_data.index,
            mappings=index_data.mappings,
            settings=index_data.settings
        )
        if result:
            return {"message": "索引创建成功"}
        else:
            raise HTTPException(status_code=500, detail="索引创建失败")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/delete-index/{index_name}")
def delete_index(
    index_name: str,
    current_user: User = Depends(get_current_active_user)
):
    """删除索引"""
    try:
        result = es_client.delete_index(index=index_name)
        if result:
            return {"message": "索引删除成功"}
        else:
            raise HTTPException(status_code=500, detail="索引删除失败")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
def get_es_health(current_user: User = Depends(get_current_active_user)):
    """获取 Elasticsearch 健康状态"""
    try:
        health = es_client.get_health()
        if health:
            return {"health": health}
        else:
            raise HTTPException(status_code=500, detail="获取健康状态失败")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
