"""
向量数据库路由 - ChromaDB 的增删查接口（需登录）

用于管理默认集合的文档，也可用于导入意图/改写规则（或直接调 /api/intent-rules/add 等）。
- POST /api/vector/add：添加文档
- POST /api/vector/query：相似度检索
- DELETE /api/vector/delete：按 id 或条件删除
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from core.vector_db import vector_db
from core.auth import get_current_active_user
from models.user import User

router = APIRouter(prefix="/api/vector", tags=["向量数据库"])


class DocumentAdd(BaseModel):
    """文档添加模型"""
    documents: List[str]
    metadatas: Optional[List[dict]] = None
    ids: Optional[List[str]] = None


class DocumentQuery(BaseModel):
    """文档查询模型"""
    query_texts: Optional[List[str]] = None
    n_results: int = 5
    where: Optional[dict] = None


class DocumentDelete(BaseModel):
    """文档删除模型"""
    ids: Optional[List[str]] = None
    where: Optional[dict] = None


@router.post("/add")
def add_documents(
    document_data: DocumentAdd,
    current_user: User = Depends(get_current_active_user)
):
    """添加文档到默认向量集合；不传 ids 时自动生成。"""
    try:
        result = vector_db.add_documents(
            documents=document_data.documents,
            metadatas=document_data.metadatas,
            ids=document_data.ids
        )
        if result:
            return {"message": "文档添加成功", "count": len(document_data.documents)}
        else:
            raise HTTPException(status_code=500, detail="文档添加失败")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query")
def query_documents(
    query_data: DocumentQuery,
    current_user: User = Depends(get_current_active_user)
):
    """按文本相似度检索，返回最相似的 n_results 条。"""
    try:
        results = vector_db.query(
            query_texts=query_data.query_texts,
            n_results=query_data.n_results,
            where=query_data.where
        )
        if results:
            return {"results": results}
        else:
            raise HTTPException(status_code=500, detail="查询失败")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/delete")
def delete_documents(
    delete_data: DocumentDelete,
    current_user: User = Depends(get_current_active_user)
):
    """按 ids 或 where 条件从默认集合删除文档。"""
    try:
        result = vector_db.delete(ids=delete_data.ids, where=delete_data.where)
        if result:
            return {"message": "文档删除成功"}
        else:
            raise HTTPException(status_code=500, detail="文档删除失败")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
