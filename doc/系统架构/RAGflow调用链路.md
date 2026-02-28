# RAGflow 调用链路说明

前端出现「RAGflow 调用失败：HTTP 404」时，可按此链路排查。

## 1. 调用链路（从前端到 RAGflow）

```
前端 (web/static/index.html)
  → 用户发送消息 → handleSend()
  → fetch(POST  /api/chat, { user_id, query })
       ↓
routers/chat.py  POST /api/chat
  → 根据 settings.USE_LANGCHAIN_RAG 二选一：
       ↓
  [A] USE_LANGCHAIN_RAG=False（默认）
      → services/rag/pipeline.py  run_chat_pipeline()
        → 意图识别、问题改写
        → app/ragflow_client.py  call_ragflow(rewritten_query)   ← 这里请求 RAGflow
        → app/answer_engine.py   generate_answer()
        → 合规、日志、返回

  [B] USE_LANGCHAIN_RAG=True
      → services/rag/langchain_chain.py  run_chat_with_langchain()
        → RAGflowRetriever.get_relevant_documents()
        → services/rag/_ragflow.py  call_ragflow(query)   ← 这里请求 RAGflow
        → DashScopeLLM 生成答案 → 合规、日志、返回
       ↓
RAGflow 实际 HTTP 请求（两处实现逻辑一致）：
  → POST {RAGFLOW_API_URL}  (配置里必须是完整检索地址，见下)
  → Body: 见「请求体与 RAGflow 官方约定」
  → 若返回非 200，则 result["error"] = "RAGflow 调用失败：HTTP 404"
       ↓
routers/chat.py
  → if "error" in result: return ChatResponse(code=500, message=result["error"])
       ↓
前端
  → data.code !== 200 时展示 data.message → 用户看到「RAGflow 调用失败：HTTP 404」
```

## 2. 涉及文件一览

| 环节           | 文件路径 |
|----------------|----------|
| 前端请求       | `web/static/index.html`（handleSend → fetch `/api/chat`） |
| 接口入口       | `routers/chat.py`（POST /api/chat） |
| 默认流水线     | `services/rag/pipeline.py`（run_chat_pipeline） |
| LangChain 流水线 | `services/rag/langchain_chain.py`（run_chat_with_langchain） |
| RAGflow 调用（app） | `app/ragflow_client.py`（call_ragflow） |
| RAGflow 调用（services） | `services/rag/_ragflow.py`（call_ragflow） |
| 配置           | `config/settings.py`（RAGFLOW_*） |

## 3. HTTP 404 的常见原因与修复

- **原因**：RAGflow 官方检索接口是 **POST `/api/v1/retrieval`**，而不是 POST `/api/v1`。  
  若 `RAGFLOW_API_URL` 配成 `http://host:9380/api/v1`，请求会发到 `/api/v1`，RAGflow 返回 404。

- **修复**：
  1. 将 `RAGFLOW_API_URL` 配成**完整检索地址**，例如：  
     `http://47.118.30.223:9380/api/v1/retrieval`
  2. 或在代码里对 base_url 自动追加 `/retrieval`（本项目已支持：若 URL 不以 `/retrieval` 结尾则自动追加）。
  3. 请求体需符合 RAGflow 文档：`question`（不是 query）、`dataset_ids`（数组），见 `app/ragflow_client.py` 与官方文档。

## 4. RAGflow 官方检索接口约定（摘要）

- **方法/路径**：`POST /api/v1/retrieval`
- **请求体**：`question`（ string ）、`dataset_ids`（ array of string ）、可选 `top_k`、`metadata_condition` 等
- **响应**：成功时 `data.chunks[]`，每个 chunk 含 `content`、`document_keyword` 等

详见：<https://ragflow.io/docs/http_api_reference> 中 “Retrieve chunks” 一节。
