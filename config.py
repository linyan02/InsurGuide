# 配置层统一入口，兼容旧导入（例如 main.py 里可能写 from config import settings）
# 实际配置定义在 config/settings.py，这里只是转发，方便根目录也能用
from config.settings import settings

__all__ = ["settings"]
