"""
Database helpers with SQLite/MySQL support based on environment configuration.
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
    if not url:
        return False
    scheme = url.split("://", 1)[0]
    return scheme.startswith("mysql")


def _parse_mysql_url(url: str) -> dict:
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
    return {
        "maxconnections": int(os.getenv("DB_POOL_MAX", "10")),
        "mincached": int(os.getenv("DB_POOL_MIN", "1")),
        "maxcached": int(os.getenv("DB_POOL_MAX_CACHED", "5")),
        "blocking": True,
    }


def _get_timeouts() -> dict:
    return {
        "connect_timeout": int(os.getenv("DB_CONNECT_TIMEOUT", "5")),
        "read_timeout": int(os.getenv("DB_READ_TIMEOUT", "10")),
        "write_timeout": int(os.getenv("DB_WRITE_TIMEOUT", "10")),
    }


def _get_mysql_pool(url: str, dict_cursor: bool) -> object:
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
    return _is_mysql_url(get_database_url())


def is_security_mysql() -> bool:
    return _is_mysql_url(get_security_database_url())


def _connect_mysql(url: str, dict_cursor: bool) -> _ConnectionProxy:
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
    conn = sqlite3.connect(path)
    if dict_cursor:
        conn.row_factory = sqlite3.Row
    return _ConnectionProxy(conn, "sqlite")


def open_connection(dict_cursor: bool = False) -> _ConnectionProxy:
    url = get_database_url()
    if _is_mysql_url(url):
        return _connect_mysql(url, dict_cursor)
    return _connect_sqlite(get_database_path(), dict_cursor)


def open_security_connection(dict_cursor: bool = False) -> _ConnectionProxy:
    url = get_security_database_url()
    if _is_mysql_url(url):
        return _connect_mysql(url, dict_cursor)
    return _connect_sqlite(get_security_db_path(), dict_cursor)


@contextmanager
def get_connection(dict_cursor: bool = False) -> Iterator[_ConnectionProxy]:
    conn = open_connection(dict_cursor=dict_cursor)
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def get_security_connection(dict_cursor: bool = False) -> Iterator[_ConnectionProxy]:
    conn = open_security_connection(dict_cursor=dict_cursor)
    try:
        yield conn
    finally:
        conn.close()
