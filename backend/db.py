"""
Database helpers with SQLite/MySQL support based on environment configuration.

本模块封装数据库连接细节，提供：
- SQLite（文件）与 MySQL（连接字符串）两种模式的统一接口
- `?` 参数占位符的兼容转换（MySQL 使用 `%s`）
- 可选连接池（DBUtils）
"""

from __future__ import annotations

from contextlib import contextmanager
import os
import sqlite3
import threading
import time
from typing import Iterator, Optional
from urllib.parse import urlparse, unquote

import pymysql
from pymysql.cursors import DictCursor
try:
    try:
        from DBUtils.PooledDB import PooledDB
    except ImportError:  # pragma: no cover
        from dbutils.pooled_db import PooledDB
except ImportError:
    PooledDB = None

from backend.config import (
    get_database_path,
    get_security_db_path,
    get_database_url,
    get_security_database_url,
)


def _is_mysql_url(url: str) -> bool:
    """
    判断连接字符串是否为 MySQL。

    Args:
        url: 连接字符串（例如 `mysql+pymysql://user:pass@host:3306/db`）

    Returns:
        是否为 MySQL URL。
    """
    if not url:
        return False
    scheme = url.split("://", 1)[0]
    return scheme.startswith("mysql")


def _parse_mysql_url(url: str) -> dict:
    """
    解析 MySQL 连接字符串为连接参数字典。

    Args:
        url: MySQL URL

    Returns:
        连接参数字典（host/port/user/password/database）。

    Raises:
        ValueError: URL 缺少必要信息时抛出。
    """
    parsed = urlparse(url)
    if not parsed.hostname or not parsed.path:
        raise ValueError("Invalid MySQL DATABASE_URL")
    return {
        "host": parsed.hostname,
        "port": parsed.port or 3306,
        "user": unquote(parsed.username) if parsed.username else "",
        "password": unquote(parsed.password) if parsed.password else "",
        "database": parsed.path.lstrip("/"),
    }


def _normalize_query(query: str, driver: str) -> str:
    """
    归一化 SQL 占位符格式。

    Args:
        query: 使用 `?` 占位符的 SQL（SQLite 风格）
        driver: "sqlite" 或 "mysql"

    Returns:
        适配目标驱动的 SQL 字符串（MySQL 会将 `?` 替换为 `%s`）。
    """
    if driver == "mysql":
        return query.replace("?", "%s")
    return query


class _CursorProxy:
    def __init__(self, cursor, driver: str) -> None:
        self._cursor = cursor
        self._driver = driver

    def execute(self, query: str, params: Optional[object] = None):
        query = _normalize_query(query, self._driver)
        if params is None:
            return self._cursor.execute(query)
        return self._cursor.execute(query, params)

    def executemany(self, query: str, params_list):
        query = _normalize_query(query, self._driver)
        return self._cursor.executemany(query, params_list)

    def __getattr__(self, name: str):
        return getattr(self._cursor, name)


class _ConnectionProxy:
    def __init__(self, conn, driver: str) -> None:
        self._conn = conn
        self._driver = driver

    def cursor(self):
        return _CursorProxy(self._conn.cursor(), self._driver)

    def __getattr__(self, name: str):
        return getattr(self._conn, name)


_pool_lock = threading.Lock()
_mysql_pools: dict[str, object] = {}


def _get_pool_settings() -> dict:
    """从环境变量读取连接池配置并返回字典。"""
    return {
        "maxconnections": int(os.getenv("DB_POOL_MAX", "10")),
        "mincached": int(os.getenv("DB_POOL_MIN", "1")),
        "maxcached": int(os.getenv("DB_POOL_MAX_CACHED", "5")),
        "blocking": True,
    }


def _get_timeouts() -> dict:
    """从环境变量读取连接超时配置并返回字典。"""
    return {
        "connect_timeout": int(os.getenv("DB_CONNECT_TIMEOUT", "5")),
        "read_timeout": int(os.getenv("DB_READ_TIMEOUT", "10")),
        "write_timeout": int(os.getenv("DB_WRITE_TIMEOUT", "10")),
    }


def _get_mysql_pool(url: str, dict_cursor: bool) -> object:
    """
    获取（并缓存）MySQL 连接池实例。

    Args:
        url: MySQL URL
        dict_cursor: 是否使用 DictCursor

    Returns:
        DBUtils 的连接池对象。

    Raises:
        ImportError: 当未安装 DBUtils 时抛出。
    """
    if PooledDB is None:
        raise ImportError("MySQL support requires 'DBUtils' package. Please install it.")
    key = f"{url}|dict={int(dict_cursor)}"
    with _pool_lock:
        pool = _mysql_pools.get(key)
        if pool:
            return pool
        settings = _parse_mysql_url(url)
        cursorclass = DictCursor if dict_cursor else None
        pool = PooledDB(
            creator=pymysql,
            **_get_pool_settings(),
            host=settings["host"],
            port=settings["port"],
            user=settings["user"],
            password=settings["password"],
            database=settings["database"],
            charset="utf8mb4",
            cursorclass=cursorclass,
            autocommit=False,
            **_get_timeouts(),
        )
        _mysql_pools[key] = pool
        return pool


def is_mysql() -> bool:
    """
    判断业务数据库是否使用 MySQL。

    Returns:
        True 表示当前业务库使用 MySQL；否则为 SQLite。
    """
    return _is_mysql_url(get_database_url())


def is_security_mysql() -> bool:
    """
    判断安全数据库是否使用 MySQL。

    Returns:
        True 表示当前安全库使用 MySQL；否则为 SQLite。
    """
    return _is_mysql_url(get_security_database_url())


def _connect_mysql(url: str, dict_cursor: bool) -> _ConnectionProxy:
    """
    建立 MySQL 连接（可选使用连接池，并带重试机制）。

    Args:
        url: MySQL URL
        dict_cursor: 是否启用 DictCursor

    Returns:
        连接代理对象（用于统一 cursor/execute 接口）。
    """
    retries = max(1, int(os.getenv("DB_CONNECT_RETRIES", "2")))
    delay = float(os.getenv("DB_CONNECT_RETRY_DELAY", "0.5"))
    use_pool = os.getenv("DB_POOL_ENABLED", "1") not in ("0", "false", "False")

    last_error = None
    for attempt in range(1, retries + 1):
        try:
            if use_pool:
                pool = _get_mysql_pool(url, dict_cursor)
                conn = pool.connection()
            else:
                settings = _parse_mysql_url(url)
                cursorclass = DictCursor if dict_cursor else None
                conn = pymysql.connect(
                    host=settings["host"],
                    port=settings["port"],
                    user=settings["user"],
                    password=settings["password"],
                    database=settings["database"],
                    charset="utf8mb4",
                    cursorclass=cursorclass,
                    autocommit=False,
                    **_get_timeouts(),
                )
            return _ConnectionProxy(conn, "mysql")
        except Exception as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(delay)
    raise last_error


def _connect_sqlite(path: str, dict_cursor: bool) -> _ConnectionProxy:
    """
    建立 SQLite 连接。

    Args:
        path: SQLite 数据库文件路径
        dict_cursor: 是否返回 sqlite3.Row（便于 dict 化）

    Returns:
        连接代理对象。
    """
    conn = sqlite3.connect(path)
    if dict_cursor:
        conn.row_factory = sqlite3.Row
    return _ConnectionProxy(conn, "sqlite")


def open_connection(dict_cursor: bool = False) -> _ConnectionProxy:
    """
    打开业务数据库连接（根据环境变量自动选择 SQLite/MySQL）。

    Args:
        dict_cursor: 是否使用字典游标

    Returns:
        连接代理对象（需要调用方负责 close）。
    """
    url = get_database_url()
    if _is_mysql_url(url):
        return _connect_mysql(url, dict_cursor)
    return _connect_sqlite(get_database_path(), dict_cursor)


def open_security_connection(dict_cursor: bool = False) -> _ConnectionProxy:
    """
    打开安全数据库连接（根据环境变量自动选择 SQLite/MySQL）。

    Args:
        dict_cursor: 是否使用字典游标

    Returns:
        连接代理对象（需要调用方负责 close）。
    """
    url = get_security_database_url()
    if _is_mysql_url(url):
        return _connect_mysql(url, dict_cursor)
    return _connect_sqlite(get_security_db_path(), dict_cursor)


@contextmanager
def get_connection(dict_cursor: bool = False) -> Iterator[_ConnectionProxy]:
    """
    以 contextmanager 方式获取业务数据库连接。

    Args:
        dict_cursor: 是否使用字典游标

    Yields:
        连接代理对象；退出上下文时自动关闭连接。
    """
    conn = open_connection(dict_cursor=dict_cursor)
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def get_security_connection(dict_cursor: bool = False) -> Iterator[_ConnectionProxy]:
    """
    以 contextmanager 方式获取安全数据库连接。

    Args:
        dict_cursor: 是否使用字典游标

    Yields:
        安全库连接代理对象；退出上下文时自动关闭连接。
    """
    conn = open_security_connection(dict_cursor=dict_cursor)
    try:
        yield conn
    finally:
        conn.close()
