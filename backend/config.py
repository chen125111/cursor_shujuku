"""
配置工具函数（从环境变量读取配置并提供默认值）。

本模块集中处理：
- 数据库文件路径与目录创建
- MySQL 连接字符串读取
- 备份目录
- CORS 允许来源列表
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _get_env_path(var_name: str, default_name: str) -> str:
    """
    获取“路径类”环境变量；未配置时返回仓库根目录下的默认文件名。

    Args:
        var_name: 环境变量名（例如 DATABASE_PATH）
        default_name: 默认文件名（相对 BASE_DIR）

    Returns:
        路径字符串。
    """
    value = os.getenv(var_name)
    if value:
        return value
    return str(BASE_DIR / default_name)


def ensure_parent_dir(path: str) -> None:
    """
    确保给定路径的父目录存在（不存在则创建）。

    Args:
        path: 文件路径或目录路径
    """
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)


def get_database_path() -> str:
    """
    获取业务数据库（SQLite）文件路径。

    Returns:
        数据库文件路径（会确保父目录存在）。
    """
    path = _get_env_path("DATABASE_PATH", "gas_data.db")
    ensure_parent_dir(path)
    return path


def get_security_db_path() -> str:
    """
    获取安全数据库（SQLite）文件路径（用于用户/审计/会话等）。

    Returns:
        安全库文件路径（会确保父目录存在）。
    """
    path = _get_env_path("SECURITY_DB_PATH", "security.db")
    ensure_parent_dir(path)
    return path


def get_database_url() -> str:
    """
    获取业务数据库的连接字符串（用于 MySQL 模式）。

    Returns:
        `DATABASE_URL` 的去空白字符串；未配置时返回空字符串。
    """
    return os.getenv("DATABASE_URL", "").strip()


def get_security_database_url() -> str:
    """
    获取安全数据库的连接字符串（用于 MySQL 模式）。

    Returns:
        `SECURITY_DATABASE_URL`（若设置）否则回退到 `DATABASE_URL`。
    """
    value = os.getenv("SECURITY_DATABASE_URL", "").strip()
    if value:
        return value
    return get_database_url()


def get_backup_dir() -> str:
    """
    获取备份目录路径。

    Returns:
        备份目录路径字符串（默认 BASE_DIR/backups）。
    """
    path = _get_env_path("BACKUP_DIR", "backups")
    return path


def get_cors_origins() -> list:
    """
    获取允许跨域的来源列表。

    Returns:
        来源列表（从 `CORS_ORIGINS` 按逗号分隔解析）；未配置返回空列表。
    """
    raw = os.getenv("CORS_ORIGINS", "")
    if not raw:
        return []
    return [origin.strip() for origin in raw.split(",") if origin.strip()]
