"""
Shared configuration helpers.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _get_env_path(var_name: str, default_name: str) -> str:
    """
    读取某个“路径类”环境变量。

    规则：
    - 若设置了环境变量 `var_name`，直接使用其值（允许相对/绝对路径）
    - 否则回落到项目根目录下的 `default_name`
    """
    value = os.getenv(var_name)
    if value:
        return value
    return str(BASE_DIR / default_name)


def ensure_parent_dir(path: str) -> None:
    """
    确保 path 对应的父目录存在。

    用途：
    - SQLite 文件可能位于 ./data/xxx.db 这类目录下
    - 在应用启动/测试期间自动创建目录，避免首次写入失败
    """
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)


def get_database_path() -> str:
    """
    SQLite 业务数据库文件路径。

    环境变量：
    - `DATABASE_PATH`：显式指定（默认：项目根目录下 `gas_data.db`）
    """
    path = _get_env_path("DATABASE_PATH", "gas_data.db")
    ensure_parent_dir(path)
    return path


def get_security_db_path() -> str:
    """
    SQLite 安全数据库文件路径（登录日志、审计日志、会话等）。

    环境变量：
    - `SECURITY_DB_PATH`：显式指定（默认：项目根目录下 `security.db`）
    """
    path = _get_env_path("SECURITY_DB_PATH", "security.db")
    ensure_parent_dir(path)
    return path


def get_database_url() -> str:
    """
    业务数据库 URL（MySQL）。

    环境变量：
    - `DATABASE_URL`：如 `mysql+pymysql://user:pass@host:3306/dbname`

    说明：
    - 若该值非空，`backend.db` 会优先使用 MySQL（而非 SQLite 文件）。
    """
    return os.getenv("DATABASE_URL", "").strip()


def get_security_database_url() -> str:
    """
    安全数据库 URL（MySQL）。

    环境变量：
    - `SECURITY_DATABASE_URL`：为空时自动回落到 `DATABASE_URL`
    """
    value = os.getenv("SECURITY_DATABASE_URL", "").strip()
    if value:
        return value
    return get_database_url()


def get_backup_dir() -> str:
    """
    备份目录（仅 SQLite 文件备份有效）。

    环境变量：
    - `BACKUP_DIR`：默认项目根目录下 `backups/`
    """
    path = _get_env_path("BACKUP_DIR", "backups")
    return path


def get_cors_origins() -> list:
    """
    解析 CORS origins 列表。

    环境变量：
    - `CORS_ORIGINS`：英文逗号分隔的 origin 列表，例如：
      `http://localhost:5173,http://127.0.0.1:5173`
    """
    raw = os.getenv("CORS_ORIGINS", "")
    if not raw:
        return []
    return [origin.strip() for origin in raw.split(",") if origin.strip()]
