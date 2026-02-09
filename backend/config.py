"""
Shared configuration helpers.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _get_env_path(var_name: str, default_name: str) -> str:
    value = os.getenv(var_name)
    if value:
        return value
    return str(BASE_DIR / default_name)


def ensure_parent_dir(path: str) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)


def get_database_path() -> str:
    path = _get_env_path("DATABASE_PATH", "gas_data.db")
    ensure_parent_dir(path)
    return path


def get_security_db_path() -> str:
    path = _get_env_path("SECURITY_DB_PATH", "security.db")
    ensure_parent_dir(path)
    return path


def get_database_url() -> str:
    return os.getenv("DATABASE_URL", "").strip()


def get_security_database_url() -> str:
    value = os.getenv("SECURITY_DATABASE_URL", "").strip()
    if value:
        return value
    return get_database_url()


def get_backup_dir() -> str:
    path = _get_env_path("BACKUP_DIR", "backups")
    return path


def get_cors_origins() -> list:
    raw = os.getenv("CORS_ORIGINS", "")
    if not raw:
        return []
    return [origin.strip() for origin in raw.split(",") if origin.strip()]
