"""
应用配置设置
使用 Pydantic Settings 管理配置
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


class Settings(BaseSettings):
    """应用配置类"""
    
    # 数据库配置
    DATABASE_URL: str = "sqlite+aiosqlite:///./zyk_ai_platform.db"
    
    # MySQL配置
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = "yuanpai00!"
    MYSQL_DATABASE: str = ""
    
    # JWT配置
    SECRET_KEY: str = "your-secret-key-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # 应用配置
    APP_NAME: str = "CSPM数据运营AI平台"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # 文件上传配置
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    UPLOAD_DIR: str = "uploads"
    
    # GitLab配置
    GITLAB_URL: str = ""
    GITLAB_TOKEN: str = ""
    GITLAB_MCP_TIMEOUT: int = 120

    # 浏览器MCP配置（默认使用官方 Playwright MCP Server）
    BROWSER_MCP_COMMAND: str = "npx -y @playwright/mcp@latest"
    BROWSER_MCP_TIMEOUT: int = 60
    
    # 日志配置
    LOG_LEVEL: str = "INFO"
    
    # API配置
    API_PREFIX: str = "/api/v1"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"
    )


# 创建全局配置实例
settings = Settings()


def _normalize_sqlite_url(url: str) -> str:
    prefix = "sqlite+aiosqlite:///"
    if not url.startswith(prefix):
        return url
    path = url[len(prefix):]
    if path.startswith("/"):
        return url
    backend_root = Path(__file__).resolve().parents[2]
    return f"{prefix}{(backend_root / path).as_posix()}"


settings.DATABASE_URL = _normalize_sqlite_url(settings.DATABASE_URL)

# 确保上传目录存在
Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
