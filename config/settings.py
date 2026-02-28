"""
应用配置 - 从环境变量与 .env 加载

本文件定义了整个项目用到的所有配置项。每个配置项都有默认值，
实际运行时会优先从系统环境变量或项目根目录的 .env 文件中读取，
这样可以在不改代码的情况下切换不同环境（开发/测试/生产）。
"""
from typing import Optional, List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    应用配置类。继承自 BaseSettings，会自动从 .env 和环境变量加载值。
    下面的每个变量名都可以在 .env 里写同名变量来覆盖默认值。
    """

    # ---------- 应用基础 ----------
    APP_NAME: str = "InsurGuide"       # 应用名称，用于接口返回和文档
    APP_VERSION: str = "1.0.0"           # 版本号
    DEBUG: bool = True                  # 是否调试模式（True 时 SQL 会打印到控制台）

    # ---------- JWT 登录令牌 ----------
    SECRET_KEY: str = "your-secret-key-change-this-in-production"  # 用于签发 token 的密钥，生产必须改
    ALGORITHM: str = "HS256"            # 加密算法
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30  # 登录后 token 有效时间（分钟）

    # ---------- MySQL 数据库 ----------
    # 用于存用户信息、交互日志、合规日志等
    MYSQL_HOST: str = "121.41.189.203"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = "ZhiBao123**"
    MYSQL_DATABASE: str = "insurguide"

    # ---------- Redis（多轮对话上下文） ----------
    # 用 Redis 存每个用户最近几轮「问-答」，这样下一轮回答时能结合上文
    REDIS_HOST: str = "121.41.189.203"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0                   # Redis 有多个逻辑库，0 是默认
    REDIS_PASSWORD: Optional[str] = "ZhiBao123**"
    REDIS_CONTEXT_TTL_MINUTES: int = 30  # 上下文过期时间，超时后要重新开始对话
    REDIS_MAX_HISTORY_TURNS: int = 10   # 最多保留多少轮对话，防止占用太多内存

    # ---------- RAGflow 知识库 ----------
    # RAGflow 是独立部署的知识库服务，本系统通过 HTTP 调它的接口做检索
    # 可为 base（如 http://host:9380/api/v1），代码会自动追加 /retrieval
    RAGFLOW_API_URL: str = "http://47.118.30.223:9380/api/v1"
    RAGFLOW_API_KEY: Optional[str] = "ragflow-dDrIbMcOZLzb9TlZ7WTRdkZlq-Ue_kKWI-pCPdtHKOw"   # 调用密钥，在 RAGflow 后台生成
    RAGFLOW_KNOWLEDGE_BASE_ID: Optional[str] = "7f6af9a5080c11f1a760fe457711635e"  # 要查的是哪个知识库
    RAGFLOW_TOP_K: int = 3              # 每次检索最多返回几条片段
    RAGFLOW_TIMEOUT: int = 10           # 请求超时秒数

    # ---------- 大模型与合规 ----------
    LLM_MODE: str = "api"               # api=用云端接口，local=用本机模型
    DASHSCOPE_API_KEY: Optional[str] = "sk-c164f51d9b0b4efb9f1ee529ee578ee4"   # 通义千问的 Key，用于生成答案/意图/改写
    OPENAI_API_KEY: Optional[str] = None
    VIOLATION_WORDS: str = "保证赔付,100%理赔,无风险,稳赚,必赔"  # 答案里出现这些词会被替换成「已屏蔽」

    # ---------- 意图识别与问题改写模式 ----------
    # rule=规则匹配，llm=大模型，llm_vector=大模型+向量库规则，bert=自训练 BERT 接口
    INTENT_MODE: str = "rule"
    REWRITE_MODE: str = "rule"
    INTENT_RULES_COLLECTION: str = "intent_rules"   # 存意图规则的向量集合名
    REWRITE_RULES_COLLECTION: str = "rewrite_rules"
    INTENT_VECTOR_TOP_K: int = 5        # 从向量库取几条规则给 LLM 参考
    REWRITE_VECTOR_TOP_K: int = 3
    BERT_INTENT_API_URL: Optional[str] = None      # 自训练 BERT 意图接口地址
    BERT_INTENT_TIMEOUT: float = 2.0    # BERT 请求超时，超时则用兜底策略
    BERT_INTENT_FALLBACK_MODE: str = "rule"  # BERT 失败时改用哪种模式
    BERT_INTENT_REQUEST_QUERY_KEY: Optional[str] = None  # 请求体里用户问题的字段名，空则用 text

    # ---------- Elasticsearch（可选） ----------
    ES_HOST: str = "localhost"
    ES_PORT: int = 9200
    ES_USER: Optional[str] = None
    ES_PASSWORD: Optional[str] = None
    ES_USE_SSL: bool = False

    # ---------- 向量库 ChromaDB ----------
    # 用于存意图规则、改写示例等，和 RAGflow 不是同一个
    VECTOR_DB_PATH: str = "./vector_db"  # 数据存在本机哪个目录
    VECTOR_DB_COLLECTION: str = "insurguide_collection"  # 默认集合名

    # ---------- 增强 RAG 模式 ----------
    # True：使用 LangChain 编排（RAGflowRetriever + DashScopeLLM + 可选 Chroma）；False：使用原有 pipeline
    USE_LANGCHAIN_RAG: bool = False
    # 答案输出格式：True=结构化意见（Markdown），False=沿用旧版简洁模板
    ANSWER_USE_OPINION_FORMAT: bool = True

    # ---------- 保障重叠度透视镜 ----------
    COVERAGE_OVERLAP_ENABLED: bool = True
    COVERAGE_OVERLAP_KB_ID: Optional[str] = None      # 单库时用，空则用默认 RAGFLOW_KNOWLEDGE_BASE_ID
    COVERAGE_OVERLAP_KB_IDS: Optional[str] = None   # 多库：逗号分隔 "id1,id2"
    COVERAGE_OVERLAP_TOP_K: int = 5
    COVERAGE_OVERLAP_QUERY_ENHANCE: bool = True     # 是否启用 query 增强
    COVERAGE_OVERLAP_KEYWORD: bool = True            # RAGflow 是否启用 keyword 匹配

    # ---------- 医疗条款解析与咨询 ----------
    CLAUSE_PARSE_ENABLED: bool = True
    CLAUSE_UPLOAD_MAX_SIZE: int = 10 * 1024 * 1024   # 10MB
    CLAUSE_ALLOWED_EXT: str = "pdf,doc,docx,txt"
    CLAUSE_KB_CHUNK_METHOD: str = "naive"            # naive | laws | book

    # ---------- 对话上下文压缩 ----------
    CONTEXT_COMPRESSION_ENABLED: bool = True
    CONTEXT_SELECTION_MODE: str = "hybrid"  # recent_only | similarity | hybrid
    CONTEXT_RECENT_REQUIRED: int = 1
    CONTEXT_MAX_TURNS: int = 5
    CONTEXT_TURN_ANSWER_MAX_CHARS: int = 150
    CONTEXT_TURN_QUERY_MAX_CHARS: int = 50
    CONTEXT_MAX_TOKENS: int = 800
    CONTEXT_SIMILARITY_METHOD: str = "keyword"  # keyword | embedding

    # ---------- Gradio 演示页 ----------
    GRADIO_PORT: int = 7860
    GRADIO_SHARE: bool = False
    # Gradio 前端请求后端 API 的根地址（与 main.py 启动的 API 一致）
    GRADIO_API_BASE_URL: str = "http://localhost:8000"
    # 首页 Logo 图片路径，相对项目根或绝对路径；空则使用 gradio_ui 内置占位图
    GRADIO_LOGO_PATH: str = ""

    def get_violation_words_list(self) -> List[str]:
        """把配置里的违规词字符串拆成列表，方便逐条检查。"""
        if not self.VIOLATION_WORDS:
            return []
        return [w.strip() for w in self.VIOLATION_WORDS.split(",") if w.strip()]

    class Config:
        env_file = ".env"    # 从项目根目录的 .env 读
        case_sensitive = True  # 变量名大小写敏感


# 全局唯一配置对象，别的模块都「from config import settings」用这个
settings = Settings()
