# 测试模块说明

## 结构

| 文件 | 说明 |
|------|------|
| **conftest.py** | 公共 fixture：FastAPI `TestClient`、测试用 SQLite 内存库（覆盖 `get_db`），供需 DB 的接口测试使用 |
| **test_api_health.py** | 根路径 `/`、健康检查 `/health`，不依赖 DB |
| **test_api_auth.py** | 认证：注册、登录、重复注册、错误密码、`/api/auth/me` 鉴权 |
| **test_api_chat.py** | 对话接口：缺参校验、返回结构、`/api/chat/clear` |
| **test_services_rag.py** | 增强 RAG：融合层 `fusion`、精排层 `rerank` 单元测试 |
| **test_app_compliance.py** | 合规：`check_and_mask`、违规词列表 |
| **test_config.py** | 配置与常量：`settings`、`ALL_INTENTS`、`INTENT_LABELS_CN` |

## 运行方式

```bash
# 项目根目录
pytest tests/ -v

# 只跑某类
pytest tests/test_api_health.py -v
pytest tests/test_services_rag.py -v

# 覆盖率
pytest tests/ --cov=config --cov=core --cov=services --cov=app --cov-report=term-missing
```

## 依赖

- `pytest`、`pytest-cov`（见 `requirements.txt`）
- 认证与对话相关测试使用 **SQLite 内存库**，无需启动 MySQL；其余接口测试不依赖外部服务。

## 扩展

- 需真实 MySQL/Redis 的集成测试可放到 `tests/integration/`，并用 `@pytest.mark.integration` 标记，默认不跑。
- 需 Mock RAGflow/LLM 的对话流水线测试可在 `tests/test_services_rag.py` 或新建 `test_pipeline.py` 中补充。
