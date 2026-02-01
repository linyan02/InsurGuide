"""
配置文件
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """应用配置"""
    
    # 应用基础配置
    APP_NAME: str = "InsurGuide"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # JWT 配置
    SECRET_KEY: str = "your-secret-key-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # MySQL 数据库配置
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = "password"
    MYSQL_DATABASE: str = "insurguide"
    
    # Elasticsearch 配置
    ES_HOST: str = "localhost"
    ES_PORT: int = 9200
    ES_USER: Optional[str] = None
    ES_PASSWORD: Optional[str] = None
    ES_USE_SSL: bool = False
    
    # 向量数据库配置 (ChromaDB)
    VECTOR_DB_PATH: str = "./vector_db"
    VECTOR_DB_COLLECTION: str = "insurguide_collection"
    
    # Gradio 配置
    GRADIO_PORT: int = 7860
    GRADIO_SHARE: bool = False
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
