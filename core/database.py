"""
MySQL 数据库连接

本模块负责：建立和 MySQL 的连接池、提供「会话」（Session）、
以及提供声明式基类 Base（models 里的表都要继承 Base）。
其他模块需要查库或写库时，通过 get_db() 拿到一次会话，用完后会自动关闭。
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from config import settings

# 拼出 MySQL 连接串：用户名:密码@主机:端口/数据库名，charset 保证中文不乱码
DATABASE_URL = (
    f"mysql+pymysql://{settings.MYSQL_USER}:{settings.MYSQL_PASSWORD}"
    f"@{settings.MYSQL_HOST}:{settings.MYSQL_PORT}/{settings.MYSQL_DATABASE}?charset=utf8mb4"
)

# 创建引擎：真正和 MySQL 通信的对象。pool_pre_ping 每次用前测一下连接是否还活着
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,   # 连接最多用 1 小时就换新的，避免被服务器踢掉
    echo=settings.DEBUG, # 调试时把执行的 SQL 打印到控制台
)

# 会话工厂：每次调用 SessionLocal() 得到一个新的「会话」，在会话里做增删改查
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 声明式基类：models/user.py、models/chat_log.py 里的表类都要继承 Base，这样 ORM 才能管理
Base = declarative_base()


def get_db():
    """
    获取数据库会话，用于 FastAPI 的依赖注入（Depends(get_db)）。
    用 yield 是为了：请求处理完后自动执行 finally，关闭会话，避免泄漏。
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
