"""
认证模块 - JWT Token 认证和密码加密

说明：
- 密码使用 PBKDF2-HMAC-SHA256（随机 salt）进行哈希存储/验证
- JWT 采用 HS256 对 payload 进行签名（不依赖第三方 JWT 库）
- 用户信息优先从安全库（`user_accounts`）读取；必要时回退到环境变量管理员账户
"""

import base64
from datetime import datetime, timedelta
import hashlib
import hmac
import json
import os
import time
from typing import Optional, Dict

from backend.db import open_security_connection
# ==================== 配置 ====================

# JWT 密钥（生产环境应使用环境变量）
DEFAULT_SECRET_KEY = "your-super-secret-key-change-in-production-2024"
SECRET_KEY = os.getenv("SECRET_KEY", DEFAULT_SECRET_KEY)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24小时

# 默认管理员账户（生产环境应存储在数据库中）
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

ADMIN_USERS = {
    ADMIN_USERNAME: {
        "username": ADMIN_USERNAME,
        "password_hash": None,
        "role": "admin",
        "created_at": "2024-01-01"
    }
}

# 角色列表
ALLOWED_ROLES = {"admin", "user"}

# ==================== 密码加密 ====================

def hash_password(password: str) -> str:
    """
    使用 PBKDF2-HMAC-SHA256 对密码进行安全哈希。

    Args:
        password: 明文密码

    Returns:
        可存储的密码哈希字符串（Base64 编码），内部格式为 `salt(32 bytes) + key`。
    """
    salt = os.urandom(32)
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt,
        100000  # 迭代次数
    )
    return base64.b64encode(salt + key).decode('utf-8')


def verify_password(password: str, password_hash: str) -> bool:
    """
    校验明文密码与已存储的 PBKDF2 哈希是否匹配。

    Args:
        password: 明文密码
        password_hash: 存储的密码哈希（Base64）

    Returns:
        是否匹配。
    """
    try:
        decoded = base64.b64decode(password_hash.encode('utf-8'))
        salt = decoded[:32]
        stored_key = decoded[32:]
        
        key = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt,
            100000
        )
        return hmac.compare_digest(key, stored_key)
    except Exception:
        return False


if ADMIN_PASSWORD:
    ADMIN_USERS[ADMIN_USERNAME]["password_hash"] = hash_password(ADMIN_PASSWORD)


def _get_user_from_db(username: str) -> Optional[Dict]:
    """
    从安全数据库读取用户信息。

    Args:
        username: 用户名

    Returns:
        用户信息字典（包含 password_hash / role / is_active 等）；不存在或异常时返回 None。
    """
    try:
        conn = open_security_connection(dict_cursor=True)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT username, password_hash, role, is_active, created_at
            FROM user_accounts WHERE username = ?
            """,
            (username,),
        )
        row = cursor.fetchone()
        conn.close()
        if not row:
            return None
        return {
            "username": row["username"],
            "password_hash": row["password_hash"],
            "role": row["role"],
            "is_active": bool(row["is_active"]),
            "created_at": row["created_at"],
        }
    except Exception:
        return None


def _upsert_user(username: str, password_hash: str, role: str, is_active: bool = True) -> None:
    """
    在安全数据库中插入或更新用户信息。

    Args:
        username: 用户名
        password_hash: 密码哈希（PBKDF2 Base64）
        role: 角色（admin/user）
        is_active: 是否启用
    """
    conn = open_security_connection(dict_cursor=True)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT username FROM user_accounts WHERE username = ?",
        (username,),
    )
    exists = cursor.fetchone()
    if exists:
        cursor.execute(
            """
            UPDATE user_accounts
            SET password_hash = ?, role = ?, is_active = ?, updated_at = CURRENT_TIMESTAMP
            WHERE username = ?
            """,
            (password_hash, role, 1 if is_active else 0, username),
        )
    else:
        cursor.execute(
            """
            INSERT INTO user_accounts (username, password_hash, role, is_active)
            VALUES (?, ?, ?, ?)
            """,
            (username, password_hash, role, 1 if is_active else 0),
        )
    conn.commit()
    conn.close()


def ensure_admin_user() -> None:
    """
    确保管理员账户存在于安全数据库中（当配置了 ADMIN_PASSWORD 时）。

    Notes:
        - 若未设置 `ADMIN_PASSWORD`，该函数不会创建/更新管理员账户。
        - 管理员用户名可通过 `ADMIN_USERNAME` 配置。
    """
    if not ADMIN_PASSWORD:
        return
    password_hash = hash_password(ADMIN_PASSWORD)
    _upsert_user(ADMIN_USERNAME, password_hash, "admin", True)


def is_admin_configured() -> bool:
    """检查管理员是否配置了密码"""
    user = _get_user_from_db(ADMIN_USERNAME)
    if user and user.get("password_hash"):
        return True
    admin = ADMIN_USERS.get(ADMIN_USERNAME)
    return bool(admin and admin.get("password_hash"))


def get_admin_username() -> str:
    """获取管理员用户名"""
    return ADMIN_USERNAME


def is_using_default_secret_key() -> bool:
    """检查是否仍在使用默认 SECRET_KEY"""
    return SECRET_KEY == DEFAULT_SECRET_KEY


# ==================== JWT Token ====================

def base64url_encode(data: bytes) -> str:
    """Base64 URL 安全编码"""
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('utf-8')


def base64url_decode(data: str) -> bytes:
    """Base64 URL 安全解码"""
    padding = 4 - len(data) % 4
    if padding != 4:
        data += '=' * padding
    return base64.urlsafe_b64decode(data.encode('utf-8'))


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    创建 JWT Token（HS256）。

    Args:
        data: 需要写入 payload 的数据（会复制一份并附加 `exp` 与 `iat`）
        expires_delta: 自定义过期时间；不传则使用默认过期配置

    Returns:
        JWT 字符串：`header.payload.signature`
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": int(expire.timestamp()),
        "iat": int(datetime.utcnow().timestamp())
    })
    
    # 创建 JWT Header
    header = {"alg": ALGORITHM, "typ": "JWT"}
    header_encoded = base64url_encode(json.dumps(header).encode('utf-8'))
    
    # 创建 JWT Payload
    payload_encoded = base64url_encode(json.dumps(to_encode).encode('utf-8'))
    
    # 创建签名
    message = f"{header_encoded}.{payload_encoded}"
    signature = hmac.new(
        SECRET_KEY.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).digest()
    signature_encoded = base64url_encode(signature)
    
    return f"{header_encoded}.{payload_encoded}.{signature_encoded}"


def verify_token(token: str) -> Optional[Dict]:
    """
    验证 JWT Token
    返回解码后的 payload，验证失败返回 None

    Args:
        token: JWT 字符串

    Returns:
        解码后的 payload（dict）；验证失败返回 None。

    Notes:
        - 校验内容包含：签名、payload JSON 解码、exp 过期时间
    """
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return None
        
        header_encoded, payload_encoded, signature_encoded = parts
        
        # 验证签名
        message = f"{header_encoded}.{payload_encoded}"
        expected_signature = hmac.new(
            SECRET_KEY.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).digest()
        
        actual_signature = base64url_decode(signature_encoded)
        
        if not hmac.compare_digest(expected_signature, actual_signature):
            return None
        
        # 解码 payload
        payload = json.loads(base64url_decode(payload_encoded).decode('utf-8'))
        
        # 检查过期时间
        if payload.get("exp", 0) < time.time():
            return None
        
        return payload
        
    except Exception:
        return None


# ==================== 用户认证 ====================

def authenticate_user(username: str, password: str) -> Optional[Dict]:
    """
    验证用户名与密码是否正确。

    Args:
        username: 用户名
        password: 明文密码

    Returns:
        登录成功返回用户信息字典（username/role）；失败返回 None。
    """
    user = _get_user_from_db(username)
    if user:
        if not user.get("is_active"):
            return None
        if not user.get("password_hash"):
            return None
        if not verify_password(password, user["password_hash"]):
            return None
        return {
            "username": user["username"],
            "role": user["role"]
        }

    user = ADMIN_USERS.get(username)
    if not user:
        return None

    if not user.get("password_hash"):
        return None

    if not verify_password(password, user["password_hash"]):
        return None

    return {
        "username": user["username"],
        "role": user["role"]
    }


def get_current_user(token: str) -> Optional[Dict]:
    """
    从 Token 获取当前用户

    Args:
        token: JWT Token（不含 Bearer 前缀）

    Returns:
        用户信息字典（username/role）；无效/过期/禁用时返回 None。
    """
    payload = verify_token(token)
    if not payload:
        return None
    
    username = payload.get("sub")
    if not username:
        return None
    
    user = _get_user_from_db(username)
    if user:
        if not user.get("is_active"):
            return None
        return {
            "username": user["username"],
            "role": user["role"]
        }

    user = ADMIN_USERS.get(username)
    if not user:
        return None
    
    return {
        "username": user["username"],
        "role": user["role"]
    }


# ==================== 用户管理 ====================

def create_user(username: str, password: str, role: str = "user") -> bool:
    """
    创建新用户

    Args:
        username: 用户名（不得与管理员内置用户重名）
        password: 明文密码（调用方应在上层执行密码策略校验）
        role: 角色（默认 user）

    Returns:
        是否创建成功（用户名已存在、角色非法等会返回 False）。
    """
    if role not in ALLOWED_ROLES:
        return False
    if username in ADMIN_USERS:
        return False

    if _get_user_from_db(username):
        return False

    password_hash = hash_password(password)
    _upsert_user(username, password_hash, role, True)
    return True


def change_password(username: str, old_password: str, new_password: str) -> bool:
    """
    修改密码

    Args:
        username: 用户名
        old_password: 原密码
        new_password: 新密码

    Returns:
        是否修改成功（原密码不匹配、用户不存在等返回 False）。
    """
    user = _get_user_from_db(username)
    if user:
        if not user.get("password_hash"):
            return False
        if not verify_password(old_password, user["password_hash"]):
            return False
        _upsert_user(username, hash_password(new_password), user["role"], user["is_active"])
        return True

    user = ADMIN_USERS.get(username)
    if not user:
        return False

    if not user.get("password_hash"):
        return False

    if not verify_password(old_password, user["password_hash"]):
        return False

    user["password_hash"] = hash_password(new_password)
    return True


def reset_user_password(username: str, new_password: str) -> bool:
    """
    管理员重置用户密码

    Args:
        username: 用户名
        new_password: 新密码

    Returns:
        是否重置成功（用户不存在则返回 False）。
    """
    user = _get_user_from_db(username)
    if user:
        _upsert_user(username, hash_password(new_password), user["role"], user["is_active"])
        return True

    user = ADMIN_USERS.get(username)
    if not user:
        return False

    user["password_hash"] = hash_password(new_password)
    return True


def list_users() -> list:
    """
    列出所有用户（不包含密码）

    Returns:
        用户列表（每项包含 username/role/is_active/created_at 等字段）。
    """
    users = []
    try:
        conn = open_security_connection(dict_cursor=True)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT username, role, is_active, created_at
            FROM user_accounts
            ORDER BY created_at ASC
            """
        )
        for row in cursor.fetchall():
            users.append({
                "username": row["username"],
                "role": row["role"],
                "is_active": bool(row["is_active"]),
                "created_at": row["created_at"],
            })
        conn.close()
    except Exception:
        pass

    if not users:
        users = [
            {
                "username": u["username"],
                "role": u["role"],
                "created_at": u["created_at"]
            }
            for u in ADMIN_USERS.values()
        ]
    return users

