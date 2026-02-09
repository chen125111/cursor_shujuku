"""
Configuration helpers.

Centralized access to environment-based settings:
- SQLite file paths and parent directory creation
- MySQL connection URLs
- backup directory path
- CORS origin list parsing
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _get_env_path(var_name: str, default_name: str) -> str:
    """
    Return a path from env, or default relative to BASE_DIR.

    Args:
        var_name: Environment variable name.
        default_name: Default file or directory name under BASE_DIR.
    """
    value = os.getenv(var_name)
    if value:
        return value
    return str(BASE_DIR / default_name)


def ensure_parent_dir(path: str) -> None:
    """Ensure parent directory exists for the given path."""
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)


def get_database_path() -> str:
    """Get SQLite database path and ensure its parent exists."""
    path = _get_env_path("DATABASE_PATH", "gas_data.db")
    ensure_parent_dir(path)
    return path


def get_security_db_path() -> str:
    """Get SQLite security database path and ensure its parent exists."""
    path = _get_env_path("SECURITY_DB_PATH", "security.db")
    ensure_parent_dir(path)
    return path


def get_database_url() -> str:
    """Get DATABASE_URL for MySQL usage (empty when unset)."""
    return os.getenv("DATABASE_URL", "").strip()


def get_security_database_url() -> str:
    """Get SECURITY_DATABASE_URL or fall back to DATABASE_URL."""
    value = os.getenv("SECURITY_DATABASE_URL", "").strip()
    if value:
        return value
    return get_database_url()


def get_backup_dir() -> str:
    """Get backup directory path."""
    path = _get_env_path("BACKUP_DIR", "backups")
    return path


def get_cors_origins() -> list:
    """Parse CORS_ORIGINS into a list of origins."""
    raw = os.getenv("CORS_ORIGINS", "")
    if not raw:
        return []
    return [origin.strip() for origin in raw.split(",") if origin.strip()]
