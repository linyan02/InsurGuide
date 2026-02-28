"""
全局常量 - 与运行环境无关的枚举、默认值等

这里放的是「意图类型」的英文标识和中文展示名。
意图识别会把用户问题归到其中一类，用于统计或后续分流，
不会随 .env 变化，所以放在 constants 里而不是 settings。
"""
# ---------- 意图英文标识（代码里用这些字符串判断） ----------
INTENT_RETRIEVAL = "retrieval"       # 查条款、规则、定义等
INTENT_CONSULTATION = "consultation" # 一般咨询、怎么办、能不能
INTENT_CLAIMS = "claims"             # 理赔相关
INTENT_UNDERWRITING = "underwriting" # 核保、健康告知
INTENT_PRODUCT = "product"          # 产品、保费、哪款好
INTENT_GREETING = "greeting"        # 你好、在吗
INTENT_OTHER = "other"              # 上面都不算时归为其他

# 所有合法意图的列表，用于校验 BERT/LLM 返回是否合法
ALL_INTENTS = [
    INTENT_RETRIEVAL,
    INTENT_CONSULTATION,
    INTENT_CLAIMS,
    INTENT_UNDERWRITING,
    INTENT_PRODUCT,
    INTENT_GREETING,
    INTENT_OTHER,
]

# 意图对应的中文名，给前端或日志展示用
INTENT_LABELS_CN = {
    INTENT_RETRIEVAL: "条款/规则检索",
    INTENT_CONSULTATION: "一般咨询",
    INTENT_CLAIMS: "理赔",
    INTENT_UNDERWRITING: "核保",
    INTENT_PRODUCT: "产品咨询",
    INTENT_GREETING: "问候",
    INTENT_OTHER: "其他",
}

# ---------- Gradio 前端调用的 API 路径（与 routers 定义一致） ----------
GRADIO_ROUTE_AUTH_LOGIN = "/api/auth/login"
GRADIO_ROUTE_AUTH_REGISTER = "/api/auth/register"
GRADIO_ROUTE_AUTH_ME = "/api/auth/me"
GRADIO_ROUTE_CHAT = "/api/chat"
GRADIO_ROUTE_CHAT_CLEAR = "/api/chat/clear"
GRADIO_ROUTE_VECTOR_QUERY = "/api/vector/query"
GRADIO_ROUTE_VECTOR_ADD = "/api/vector/add"
GRADIO_ROUTE_ES_SEARCH = "/api/es/search"
GRADIO_ROUTE_ES_INDEX = "/api/es/index"
GRADIO_ROUTE_ES_HEALTH = "/api/es/health"
# P2-10 条款解析
GRADIO_ROUTE_CLAUSE_UPLOAD = "/api/clause/upload"
GRADIO_ROUTE_CLAUSE_CONTEXT = "/api/clause/context"
GRADIO_ROUTE_CLAUSE_CLEAR = "/api/clause/clear"
GRADIO_ROUTE_CHAT_STREAM = "/api/chat/stream"
