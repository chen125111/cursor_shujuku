#!/usr/bin/env python3
"""
Apply versioned SQL migrations for gas/security databases.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from backend.db import (
    get_connection,
    get_security_connection,
    is_mysql,
    is_security_mysql,
)


BASE_DIR = Path(__file__).resolve().parent.parent
MIGRATIONS_DIR = BASE_DIR / "migrations"


def split_sql(sql: str) -> list[str]:
    statements: list[str] = []
    current: list[str] = []
    for line in sql.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("--"):
            continue
        current.append(stripped)
        if stripped.endswith(";"):
            stmt = " ".join(current).rstrip(";").strip()
            if stmt:
                statements.append(stmt)
            current = []
    if current:
        stmt = " ".join(current).strip()
        if stmt:
            statements.append(stmt)
    return statements


def ensure_schema_table(cursor) -> None:
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version VARCHAR(64) PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


def get_applied_versions(cursor) -> set[str]:
    cursor.execute("SELECT version FROM schema_migrations")
    rows = cursor.fetchall()
    return {row["version"] for row in rows}


def apply_migrations(name: str, migration_path: Path, conn_factory) -> None:
    if not migration_path.exists():
        raise RuntimeError(f"Missing migrations directory: {migration_path}")

    with conn_factory(dict_cursor=True) as conn:
        cursor = conn.cursor()
        ensure_schema_table(cursor)
        conn.commit()

        applied = get_applied_versions(cursor)
        files = sorted(migration_path.glob("*.sql"))
        if not files:
            print(f"[migrate] {name}: no migration files found")
            return

        for file in files:
            version = file.stem
            if version in applied:
                continue
            sql = file.read_text()
            for statement in split_sql(sql):
                cursor.execute(statement)
            cursor.execute(
                "INSERT INTO schema_migrations (version) VALUES (?)",
                (version,),
            )
            conn.commit()
            print(f"[migrate] {name}: applied {version}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply database migrations.")
    parser.add_argument(
        "--target",
        choices=("gas", "security", "all"),
        default="all",
        help="Which database to migrate",
    )
    args = parser.parse_args()

    if args.target in ("gas", "all"):
        if not is_mysql():
            print("[migrate] gas: DATABASE_URL is not MySQL, skipping")
        else:
            apply_migrations("gas", MIGRATIONS_DIR / "gas", get_connection)

    if args.target in ("security", "all"):
        if not is_security_mysql():
            print("[migrate] security: SECURITY_DATABASE_URL is not MySQL, skipping")
        else:
            apply_migrations("security", MIGRATIONS_DIR / "security", get_security_connection)


if __name__ == "__main__":
    main()
