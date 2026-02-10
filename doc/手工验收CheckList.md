# InsurGuide 智保灵犀 - 手工验收 CheckList

本文档用于逐项手工验收：后端 API、增强 RAG 流程、前端服务及与《详细技术实现方案》目标的一致性。  
建议按顺序执行，并在完成项前打勾 `- [x]`。

**前置条件**：已安装依赖 `pip install -r requirements.txt`，并配置 `.env`（MySQL、Redis、RAGflow、DASHSCOPE_API_KEY 等）。

---

## 一、环境与服务启动

| 序号 | 验收项 | 操作步骤 | 预期结果 | 结果 |
|------|--------|----------|----------|------|
| 1.1 | 后端 API 启动 | 在项目根目录执行 `python main.py` 或 `uvicorn api.main:app --reload --host 0.0.0.0 --port 8000` | 控制台无报错，输出包含 Uvicorn 启动信息 | ☐ |
| 1.2 | 健康检查 | 浏览器或 curl 访问 `http://localhost:8000/health` | 返回 `{"status":"healthy"}` | ☐ |
| 1.3 | 根路径 | 访问 `http://localhost:8000/` | 返回欢迎信息，含 `message`、`version`、`docs`、`web` 等 | ☐ |
| 1.4 | API 文档 | 访问 `http://localhost:8000/docs` | 打开 Swagger UI，可见各接口（/api/auth/*、/api/chat、/api/vector/*、/api/es/*、/api/intent-rules/add 等） | ☐ |
| 1.5 | Gradio 启动（可选） | 另开终端执行 `python gradio_app.py` | 控制台提示 Gradio 地址（默认 `http://0.0.0.0:7860`） | ☐ |
| 1.6 | Gradio 页面 | 浏览器访问 `http://localhost:7860` | 打开 InsurGuide 界面，可见多个 Tab（用户认证、向量数据库、ES、增强 RAG 对话、AI 对话） | ☐ |

---

## 二、认证与用户

| 序号 | 验收项 | 操作步骤 | 预期结果 | 结果 |
|------|--------|----------|----------|------|
| 2.1 | 用户注册 | `POST http://localhost:8000/api/auth/register`，Body(JSON)：`{"username":"test1","email":"test1@example.com","password":"Test123!"}` | HTTP 201，返回用户信息（id、username、email、is_active），无 password | ☐ |
| 2.2 | 重复注册 | 再次用相同 username 或 email 注册 | HTTP 400，提示“用户名已存在”或“邮箱已存在” | ☐ |
| 2.3 | 用户登录 | `POST http://localhost:8000/api/auth/login`，Body(form)：`username=test1&password=Test123!` | HTTP 200，返回 `access_token`、`token_type: bearer` | ☐ |
| 2.4 | 错误密码登录 | 使用错误密码登录 | HTTP 401，提示“用户名或密码错误” | ☐ |
| 2.5 | 获取当前用户 | `GET http://localhost:8000/api/auth/me`，Header：`Authorization: Bearer <上一步的 access_token>` | HTTP 200，返回当前用户信息 | ☐ |
| 2.6 | 无 Token 访问 /me | 不带 Authorization 访问 `/api/auth/me` | HTTP 401 | ☐ |

**curl 示例（登录后取 /me）**：
```bash
# 登录（获取 token）
curl -X POST "http://localhost:8000/api/auth/login" -d "username=test1&password=Test123!"

# 使用返回的 access_token
curl -X GET "http://localhost:8000/api/auth/me" -H "Authorization: Bearer <access_token>"
```

---

## 三、增强 RAG 对话（核心接口）

| 序号 | 验收项 | 操作步骤 | 预期结果 | 结果 |
|------|--------|----------|----------|------|
| 3.1 | 正常一问一答 | `POST http://localhost:8000/api/chat`，Body(JSON)：`{"user_id":"u001","query":"重疾险等待期一般是多久？"}` | HTTP 200，`data.answer` 有内容，`data.source` 为来源列表，`data.intent`、`data.intent_cn`、`data.rewritten_query` 等有值 | ☐ |
| 3.2 | 多轮对话（上下文） | 同一 `user_id` 再发一问，如 `{"user_id":"u001","query":"那理赔呢？"}` | 回答能结合上一轮（等待期）语境，且 `data.context_count` 递增 | ☐ |
| 3.3 | 意图与改写结果 | 查看 3.1 或 3.2 的响应 `data` | 含 `intent`、`intent_cn`、`intent_confidence`、`intent_method`；`rewritten_query`、`rewrite_changed`、`rewrite_method` | ☐ |
| 3.4 | 缺 user_id | Body 中 `user_id` 为空或缺失 | HTTP 400，提示“user_id 不能为空” | ☐ |
| 3.5 | 缺 query | Body 中 `query` 为空或缺失 | HTTP 400，提示“query 不能为空” | ☐ |
| 3.6 | RAGflow 不可用时的表现 | 关闭 RAGflow 或配置错误 URL/Key 后发问 | HTTP 200 但 `code=500` 或 `data` 中无 answer，message 提示检索/配置相关错误 | ☐ |
| 3.7 | 清除上下文 | `POST http://localhost:8000/api/chat/clear`，Body(JSON)：`{"user_id":"u001"}` | HTTP 200，提示“已清除上下文”；下一轮用同一 user_id 发问时 `context_count` 从 1 开始 | ☐ |
| 3.8 | 可选 intent_mode / rewrite_mode | `POST /api/chat`，Body：`{"user_id":"u002","query":"理赔需要什么材料？","intent_mode":"rule","rewrite_mode":"llm"}` | 正常返回，且 `data.intent_method`、`data.rewrite_method` 与传入一致或符合预期 | ☐ |

**curl 示例（对话）**：
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"u001","query":"重疾险等待期一般是多久？"}'
```

---

## 四、合规与日志（与产品技术文档一致）

| 序号 | 验收项 | 操作步骤 | 预期结果 | 结果 |
|------|--------|----------|----------|------|
| 4.1 | 违规词屏蔽 | 若知识库或模型返回内容包含配置的违规词（如“保证赔付”），或通过构造使答案含违规词 | 返回给前端的 `data.answer` 中该词被替换为“[违规表述已屏蔽]”，`data.violated` 为 true | ☐ |
| 4.2 | 合规日志落库 | 在 4.1 触发违规后，查 MySQL 表 `compliance_logs` | 有新增记录，含 user_id、query、answer_snapshot、violated=true、remark 等 | ☐ |
| 4.3 | 交互日志落库 | 任意成功一轮对话后，查 MySQL 表 `interaction_logs` | 有对应记录，含 user_id、query、answer、source_count、created_at | ☐ |

---

## 五、向量库与 ES（需登录）

以下接口需在 Header 中带 `Authorization: Bearer <token>`（先完成 2.3 登录获取 token）。

| 序号 | 验收项 | 操作步骤 | 预期结果 | 结果 |
|------|--------|----------|----------|------|
| 5.1 | 向量库添加文档 | `POST http://localhost:8000/api/vector/add`，Body：`{"documents":["测试文档内容A","测试文档内容B"],"metadatas":null,"ids":null}`，Header 带 Token | HTTP 200，提示添加成功、count=2 | ☐ |
| 5.2 | 向量库检索 | `POST http://localhost:8000/api/vector/query`，Body：`{"query_texts":["测试文档"],"n_results":5,"where":null}`，Header 带 Token | HTTP 200，`results` 中含与“测试文档”相似的内容 | ☐ |
| 5.3 | 向量库未登录 | 不带 Token 调用 5.1 或 5.2 | HTTP 401 | ☐ |
| 5.4 | ES 索引文档（若已部署 ES） | `POST http://localhost:8000/api/es/index`，Body：`{"index":"insurguide","document":{"title":"测试","content":"内容"},"doc_id":null}`，Header 带 Token | HTTP 200，提示索引成功 | ☐ |
| 5.5 | ES 搜索（若已部署 ES） | `POST http://localhost:8000/api/es/search`，Body：`{"index":"insurguide","query":{"match":{"content":"内容"}},"size":10,"from_":0}`，Header 带 Token | HTTP 200，`results` 中有命中 | ☐ |
| 5.6 | ES 健康（若已部署 ES） | `GET http://localhost:8000/api/es/health`，Header 带 Token | HTTP 200，返回集群健康信息 | ☐ |

---

## 六、意图规则与改写规则（llm_vector 模式用）

| 序号 | 验收项 | 操作步骤 | 预期结果 | 结果 |
|------|--------|----------|----------|------|
| 6.1 | 添加意图规则 | `POST http://localhost:8000/api/intent-rules/add`，Body(JSON)：`[{"content":"意图：claims。关键词：理赔、赔付、报销。说明：用户问理赔条件、流程、材料时归为此类。","rule_id":"rule_1"}]` | HTTP 200，返回 `code:200`、`count:1` | ☐ |
| 6.2 | 添加改写示例 | `POST http://localhost:8000/api/rewrite-rules/add`，Body(JSON)：`[{"content":"原问：那理赔呢。上下文：重疾险等待期。改写：重疾险理赔条件与流程。","rule_id":"rw_1"}]` | HTTP 200，返回 `code:200`、`count:1` | ☐ |
| 6.3 | 空 body | 上述接口传空数组 `[]` | HTTP 400，提示至少提供一条规则/示例 | ☐ |

---

## 七、LangChain 模式开关（USE_LANGCHAIN_RAG）

| 序号 | 验收项 | 操作步骤 | 预期结果 | 结果 |
|------|--------|----------|----------|------|
| 7.1 | 默认走原 pipeline | 确认 `.env` 中无 `USE_LANGCHAIN_RAG` 或 `USE_LANGCHAIN_RAG=false`，重启后端，发 `POST /api/chat` | 行为与之前一致，使用 `run_chat_pipeline`（RAGflow + answer_engine） | ☐ |
| 7.2 | 启用 LangChain 编排 | 设置 `USE_LANGCHAIN_RAG=true`，重启后端，发 `POST /api/chat`（同一 user_id、query） | HTTP 200，返回结构不变（answer、sources、intent*、rewritten_query 等），实际由 `run_chat_with_langchain`（RAGflowRetriever + DashScopeLLM）执行 | ☐ |
| 7.3 | 响应结构一致 | 对比 7.1 与 7.2 的响应 `data` 字段 | 均包含 answer、context_count、source、violated、intent、intent_cn、rewritten_query、rewrite_changed 等，便于前端无感切换 | ☐ |

---

## 八、Gradio 前端（与产品技术文档“Web 端”一致）

| 序号 | 验收项 | 操作步骤 | 预期结果 | 结果 |
|------|--------|----------|----------|------|
| 8.1 | 登录 Tab | 在“用户认证”Tab 输入已注册用户名、密码，点击登录 | 显示“登录成功”及 Token 摘要 | ☐ |
| 8.2 | 注册 Tab | 在“用户认证”Tab 输入新用户名、邮箱、密码，点击注册 | 显示“注册成功” | ☐ |
| 8.3 | 向量数据库 Tab | 在“向量数据库”Tab 输入 Token、查询文本、结果数量，点击查询 | 显示查询结果（需后端 API 正常且已登录） | ☐ |
| 8.4 | Elasticsearch Tab | 在“Elasticsearch”Tab 输入 Token、索引名、搜索文本，点击搜索 | 显示搜索结果（需 ES 已部署且配置正确） | ☐ |
| 8.5 | 增强 RAG 对话 Tab | 在“🦉 增强 RAG 对话”Tab 输入用户 ID、提问（如“重疾险等待期多长？”），点击发送 | 显示答案与溯源信息（当前对话轮数、意图识别、来源、是否改写等） | ☐ |
| 8.6 | 多轮对话（Gradio） | 同一用户 ID 连续问两轮（如先问等待期，再问“那理赔呢？”） | 第二轮回答能结合第一轮语境 | ☐ |
| 8.7 | AI 对话 Tab（可选） | 若已配置 OPENAI_API_KEY，在“AI 对话”Tab 输入消息发送 | 返回 LLM 回复（不经过 RAG） | ☐ |

---

## 九、与《详细技术实现方案》目标对照

以下与文档“方案目标与架构”逐条对应，验收时确认功能存在且可验证即可。

| 文档目标 | 验收要点 | 结果 |
|----------|----------|------|
| 多轮对话、上下文管理 | Redis 存 context:{user_id}，TTL 与轮数限制；/api/chat 使用同一 user_id 时 context_count 递增；/api/chat/clear 可清空 | ☐ |
| 意图识别（多模式） | rule/llm/llm_vector/bert 可配置或通过 intent_mode 传入；返回 intent、intent_cn、intent_method | ☐ |
| 问题改写（多模式） | rule/llm/llm_vector 可配置或通过 rewrite_mode 传入；返回 rewritten_query、rewrite_changed、rewrite_method | ☐ |
| RAGflow 检索 | 用改写后问题调 RAGflow，返回知识库片段与来源；答案中能体现“引用知识库” | ☐ |
| 答案生成与保险 Prompt | 结合知识库内容与历史上下文生成答案；含合规声明类表述 | ☐ |
| 合规校验 | 违规词替换为“[违规表述已屏蔽]”，violated 为 true，compliance_logs 有记录 | ☐ |
| 交互/合规日志 | interaction_logs、compliance_logs 有写入，可查库核对 | ☐ |
| 统一 API 与 Web | /api/chat 为核心接口；Gradio 提供完整 Web 演示（认证、向量、ES、增强 RAG、可选 AI 对话） | ☐ |
| LangChain 统一编排（扩展） | USE_LANGCHAIN_RAG=true 时使用 RAGflowRetriever + DashScopeLLM + 可选 Chroma，行为与文档目标一致 | ☐ |

---

## 十、快速命令汇总（便于复制）

```bash
# 1. 健康检查
curl -s http://localhost:8000/health

# 2. 注册
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"test1","email":"test1@example.com","password":"Test123!"}'

# 3. 登录（将返回的 access_token 用于后续需认证的接口）
curl -X POST http://localhost:8000/api/auth/login -d "username=test1&password=Test123!"

# 4. 增强 RAG 对话（无需登录）
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id":"u001","query":"重疾险等待期一般是多久？"}'

# 5. 清除上下文
curl -X POST http://localhost:8000/api/chat/clear \
  -H "Content-Type: application/json" \
  -d '{"user_id":"u001"}'
```

---

**文档版本**：与当前代码分支一致，验收完成后可标注日期与验收人。
