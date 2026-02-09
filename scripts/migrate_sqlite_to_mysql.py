#!/usr/bin/env python3
"""
Migrate SQLite data into MySQL (RDS) using existing schema.
"""

from __future__ import annotations

import argparse
import os
import sqlite3
from pathlib import Path
from typing import Iterable, List

from backend.db import get_connection, get_security_connection, is_mysql, is_security_mysql


GAS_TABLES = ["gas_mixture", "pending_review"]
SECURITY_TABLES = [
    "login_logs",
    "audit_logs",
    "data_history",
    "sessions",
    "blocked_ips",
    "user_totp",
    "user_accounts",
]


def chunked(items: List[sqlite3.Row], size: int) -> Iterable[List[sqlite3.Row]]:
    for i in range(0, len(items), size):
        yield items[i : i + size]


def table_exists(conn: sqlite3.Connection, table: str) -> bool:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name = ?",
        (table,),
    )
    return cursor.fetchone() is not None


def quote_ident(name: str) -> str:
    return f"`{name}`"


def copy_table(
    sqlite_conn: sqlite3.Connection,
    mysql_conn_factory,
    table: str,
    batch_size: int,
    force: bool,
) -> None:
    if not table_exists(sqlite_conn, table):
        print(f"[migrate] sqlite missing table: {table}, skip")
        return

    cursor = sqlite_conn.cursor()
    cursor.execute(f"SELECT * FROM {table}")
    rows = cursor.fetchall()
    if not rows:
        print(f"[migrate] {table}: no rows")
        return

    columns = [col[0] for col in cursor.description]
    columns_sql = ", ".join(quote_ident(col) for col in columns)
    table_sql = quote_ident(table)
    placeholders = ", ".join(["?"] * len(columns))
    insert_sql = f"INSERT INTO {table_sql} ({columns_sql}) VALUES ({placeholders})"

    with mysql_conn_factory(dict_cursor=True) as mysql_conn:
        mysql_cursor = mysql_conn.cursor()
        mysql_cursor.execute(f"SELECT COUNT(*) as count FROM {table_sql}")
        count_row = mysql_cursor.fetchone()
        existing = count_row["count"] if count_row else 0
        if existing and not force:
            print(f"[migrate] {table}: target not empty ({existing} rows), skip")
            return
        if existing and force:
            mysql_cursor.execute(f"TRUNCATE TABLE {table_sql}")
            mysql_conn.commit()

        for batch in chunked(rows, batch_size):
            mysql_cursor.executemany(
                insert_sql,
                [tuple(row) for row in batch],
            )
            mysql_conn.commit()

    print(f"[migrate] {table}: copied {len(rows)} rows")


def run_migration(
    sqlite_path: Path,
    mysql_conn_factory,
    tables: List[str],
    batch_size: int,
    force: bool,
) -> None:
    if not sqlite_path.exists():
        print(f"[migrate] sqlite not found: {sqlite_path}")
        return

    sqlite_conn = sqlite3.connect(str(sqlite_path))
    sqlite_conn.row_factory = sqlite3.Row
    try:
        for table in tables:
            copy_table(sqlite_conn, mysql_conn_factory, table, batch_size, force)
    finally:
        sqlite_conn.close()


def init_mysql_schema() -> None:
    from backend.database import init_database
    from backend.data_review import init_review_tables
    from backend.security import init_security_db
    from backend.totp import init_totp_table

    init_database()
    init_review_tables()
    init_security_db()
    init_totp_table()


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate SQLite data into MySQL.")
    parser.add_argument(
        "--gas-sqlite",
        default="gas_data.db",
        help="Path to gas_data.db",
    )
    parser.add_argument(
        "--security-sqlite",
        default="security.db",
        help="Path to security.db",
    )
    parser.add_argument("--database-url", default="", help="MySQL DATABASE_URL")
    parser.add_argument(
        "--security-database-url",
        default="",
        help="MySQL SECURITY_DATABASE_URL (optional)",
    )
    parser.add_argument("--batch-size", type=int, default=1000)
    parser.add_argument("--force", action="store_true", help="Truncate target tables before insert")
    args = parser.parse_args()

    if args.database_url:
        os.environ["DATABASE_URL"] = args.database_url
    if args.security_database_url:
        os.environ["SECURITY_DATABASE_URL"] = args.security_database_url

    if not is_mysql():
        raise SystemExit("DATABASE_URL is not MySQL, aborting.")
    if not is_security_mysql():
        raise SystemExit("SECURITY_DATABASE_URL is not MySQL, aborting.")

    init_mysql_schema()

    run_migration(
        Path(args.gas_sqlite),
        get_connection,
        GAS_TABLES,
        args.batch_size,
        args.force,
    )
    run_migration(
        Path(args.security_sqlite),
        get_security_connection,
        SECURITY_TABLES,
        args.batch_size,
        args.force,
    )


if __name__ == "__main__":
    main()
