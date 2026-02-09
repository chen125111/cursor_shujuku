from __future__ import annotations

import importlib
import os
from pathlib import Path
from typing import Iterator

import pytest

# 关键环境变量需要在 *导入 backend.* 之前* 设置，
# 否则 backend/auth.py 等模块会在 import 时缓存 os.getenv 的结果。
os.environ.setdefault("CACHE_ENABLED", "0")
os.environ.setdefault("REDIS_URL", "")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("ADMIN_USERNAME", "admin")
os.environ.setdefault("ADMIN_PASSWORD", "AdminPass123")
os.environ.setdefault("BACKUP_ENABLED", "0")


@pytest.fixture(scope="session")
def test_db_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return tmp_path_factory.mktemp("db")


@pytest.fixture(scope="session", autouse=True)
def _session_env(test_db_dir: Path) -> Iterator[None]:
    """
    为测试会话设置隔离环境变量，避免污染本地/生产数据库。
    注意：后端模块存在“导入即初始化数据库”的副作用，因此测试代码需在此之后再导入 backend.*。
    """
    mp = pytest.MonkeyPatch()
    mp.setenv("DATABASE_PATH", str(test_db_dir / "gas_test.db"))
    mp.setenv("SECURITY_DB_PATH", str(test_db_dir / "security_test.db"))
    mp.delenv("DATABASE_URL", raising=False)
    mp.delenv("SECURITY_DATABASE_URL", raising=False)

    yield
    mp.undo()


@pytest.fixture()
def init_databases() -> None:
    """
    初始化业务数据库/安全数据库（幂等）。
    """
    # 延迟导入，确保使用测试环境变量
    from backend import database as database_module
    from backend import security as security_module
    from backend import data_review as data_review_module

    importlib.reload(database_module)
    importlib.reload(security_module)
    importlib.reload(data_review_module)

    security_module.init_security_db()
    database_module.init_database()
    data_review_module.init_review_tables()


@pytest.fixture()
def reset_databases(init_databases: None) -> None:
    """
    清空两套数据库，确保用例之间互不影响。
    """
    from backend.db import get_connection, get_security_connection

    with get_connection(dict_cursor=True) as conn:
        cur = conn.cursor()
        # 业务库表
        cur.execute("DELETE FROM gas_mixture")
        cur.execute("DELETE FROM pending_review")
        conn.commit()

    with get_security_connection(dict_cursor=True) as conn:
        cur = conn.cursor()
        # 安全库表
        cur.execute("DELETE FROM login_logs")
        cur.execute("DELETE FROM audit_logs")
        cur.execute("DELETE FROM data_history")
        cur.execute("DELETE FROM sessions")
        cur.execute("DELETE FROM blocked_ips")
        cur.execute("DELETE FROM user_accounts")
        conn.commit()


@pytest.fixture()
def sample_record() -> dict:
    # 满足 data_validation：摩尔分数之和为 1.0
    return {
        "temperature": 300.0,
        "pressure": 10.0,
        "x_ch4": 0.8,
        "x_c2h6": 0.1,
        "x_c3h8": 0.05,
        "x_co2": 0.03,
        "x_n2": 0.01,
        "x_h2s": 0.005,
        "x_ic4h10": 0.005,
    }
