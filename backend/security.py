"""
安全模块 - API限流、防爬虫、登录日志、会话管理、密码策略
"""

import time
import hashlib
import hmac
import base64
import re
import os
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
from collections import defaultdict
import threading

try:
    import redis
except ImportError:  # pragma: no cover
    redis = None

from backend.db import get_security_connection, is_security_mysql, open_security_connection

# ==================== 配置 ====================

# API 限流配置
RATE_LIMIT_WINDOW = 60  # 时间窗口（秒）
RATE_LIMIT_MAX_REQUESTS = 60  # 每个窗口最大请求数
RATE_LIMIT_BLOCK_DURATION = 300  # 封禁时长（秒）

# 登录限制
LOGIN_MAX_ATTEMPTS = 5  # 最大登录尝试次数
LOGIN_BLOCK_DURATION = 900  # 登录封禁时长（秒）15分钟

# 密码策略
PASSWORD_MIN_LENGTH = 8
PASSWORD_REQUIRE_UPPERCASE = True
PASSWORD_REQUIRE_LOWERCASE = True
PASSWORD_REQUIRE_DIGIT = True
PASSWORD_REQUIRE_SPECIAL = False

# 会话配置
SESSION_MAX_AGE = 24 * 60 * 60  # 24小时
SESSION_MAX_PER_USER = 5  # 每用户最大会话数

# 爬虫检测
CRAWLER_USER_AGENTS = [
    'bot', 'crawler', 'spider', 'scraper', 'curl', 'wget', 'python-requests',
    'scrapy', 'httpclient', 'java', 'axios', 'node-fetch', 'go-http-client'
]

# Redis 配置
REDIS_URL = os.getenv("REDIS_URL", "").strip()
REDIS_PREFIX = os.getenv("REDIS_PREFIX", "gasapp").strip() or "gasapp"

CRAWLER_PATTERNS = [
    r'/api/records\?.*per_page=(100|[5-9]\d{2,})',  # 大量数据请求
    r'page=\d{3,}',  # 深度分页
]

# ==================== 内存存储 ====================

# 请求计数器 {ip: [(timestamp, count), ...]}
request_counter: Dict[str, List[Tuple[float, int]]] = defaultdict(list)

# 封禁列表 {ip: unblock_timestamp}
blocked_ips: Dict[str, float] = {}

# 登录尝试 {ip: [(timestamp, success), ...]}
login_attempts: Dict[str, List[Tuple[float, bool]]] = defaultdict(list)

# 活跃会话 {token_hash: session_info}
active_sessions: Dict[str, Dict] = {}

# 锁
_lock = threading.Lock()
_redis_lock = threading.Lock()
_redis_client = None


def _redis_key(suffix: str) -> str:
    return f"{REDIS_PREFIX}:{suffix}"


def get_redis_client():
    global _redis_client
    if not REDIS_URL or redis is None:
        return None
    with _redis_lock:
        if _redis_client is None:
            try:
                _redis_client = redis.Redis.from_url(
                    REDIS_URL,
                    decode_responses=True,
                )
            except Exception:
                _redis_client = None
        return _redis_client


# ==================== 数据库初始化 ====================

def _ensure_index(cursor, table: str, index_name: str, columns: str) -> None:
    if is_security_mysql():
        cursor.execute(
            """
            SELECT COUNT(1) as count
            FROM information_schema.statistics
            WHERE table_schema = DATABASE()
              AND table_name = ?
              AND index_name = ?
            """,
            (table, index_name),
        )
        row = cursor.fetchone()
        if not row or row["count"] == 0:
            cursor.execute(f"CREATE INDEX {index_name} ON {table}({columns})")
    else:
        cursor.execute(f"CREATE INDEX IF NOT EXISTS {index_name} ON {table}({columns})")

def init_security_db():
    """初始化安全数据库"""
    id_column = "BIGINT PRIMARY KEY AUTO_INCREMENT" if is_security_mysql() else "INTEGER PRIMARY KEY AUTOINCREMENT"
    username_type = "VARCHAR(64)" if is_security_mysql() else "TEXT"
    ip_type = "VARCHAR(45)" if is_security_mysql() else "TEXT"
    token_type = "VARCHAR(64)" if is_security_mysql() else "TEXT"
    action_type = "VARCHAR(64)" if is_security_mysql() else "TEXT"
    resource_type = "VARCHAR(128)" if is_security_mysql() else "TEXT"
    field_type = "VARCHAR(64)" if is_security_mysql() else "TEXT"
    with get_security_connection(dict_cursor=True) as conn:
        cursor = conn.cursor()
    
        # 登录日志表
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS login_logs (
                id {id_column},
                username {username_type} NOT NULL,
                ip_address {ip_type} NOT NULL,
                user_agent TEXT,
                success INTEGER NOT NULL,
                failure_reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    
        # 操作审计日志表
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS audit_logs (
                id {id_column},
                username {username_type} NOT NULL,
                action {action_type} NOT NULL,
                resource {resource_type},
                resource_id INTEGER,
                old_value TEXT,
                new_value TEXT,
                ip_address {ip_type},
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    
        # 数据历史表
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS data_history (
                id {id_column},
                record_id INTEGER NOT NULL,
                action {action_type} NOT NULL,
                field_name {field_type},
                old_value TEXT,
                new_value TEXT,
                username {username_type},
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    
        # 会话表
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS sessions (
                id {id_column},
                token_hash {token_type} UNIQUE NOT NULL,
                username {username_type} NOT NULL,
                ip_address {ip_type},
                user_agent TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL
            )
        ''')
    
        # 封禁IP表
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS blocked_ips (
                id {id_column},
                ip_address {ip_type} UNIQUE NOT NULL,
                reason TEXT,
                blocked_until TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS user_accounts (
                id {id_column},
                username {username_type} UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role {action_type} NOT NULL,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    
        # 创建索引
        _ensure_index(cursor, "login_logs", "idx_login_logs_username", "username")
        _ensure_index(cursor, "login_logs", "idx_login_logs_ip", "ip_address")
        _ensure_index(cursor, "audit_logs", "idx_audit_logs_username", "username")
        _ensure_index(cursor, "data_history", "idx_data_history_record", "record_id")
        _ensure_index(cursor, "sessions", "idx_sessions_username", "username")
        _ensure_index(cursor, "user_accounts", "idx_user_accounts_username", "username")

        conn.commit()
    print("[Security] 安全数据库初始化完成")


# ==================== API 限流 ====================

def check_rate_limit(ip: str) -> Tuple[bool, str]:
    """
    检查API限流
    返回: (是否允许, 错误信息)
    """
    current_time = time.time()
    redis_client = get_redis_client()
    if redis_client:
        blocked_key = _redis_key(f"blocked:{ip}")
        ttl = redis_client.ttl(blocked_key)
        if ttl and ttl > 0:
            return False, f"IP已被临时封禁，请在{ttl}秒后重试"

        window = int(current_time // RATE_LIMIT_WINDOW)
        rate_key = _redis_key(f"rate:{ip}:{window}")
        count = redis_client.incr(rate_key)
        if count == 1:
            redis_client.expire(rate_key, RATE_LIMIT_WINDOW + 1)

        if count > RATE_LIMIT_MAX_REQUESTS:
            redis_client.setex(blocked_key, RATE_LIMIT_BLOCK_DURATION, "rate_limit")
            return False, f"请求过于频繁，已被临时封禁{RATE_LIMIT_BLOCK_DURATION}秒"
        return True, ""

    with _lock:
        # 检查是否被封禁
        if ip in blocked_ips:
            if current_time < blocked_ips[ip]:
                remaining = int(blocked_ips[ip] - current_time)
                return False, f"IP已被临时封禁，请在{remaining}秒后重试"
            else:
                del blocked_ips[ip]

        # 清理过期记录
        cutoff = current_time - RATE_LIMIT_WINDOW
        request_counter[ip] = [(t, c) for t, c in request_counter[ip] if t > cutoff]

        # 计算当前窗口请求数
        total_requests = sum(c for t, c in request_counter[ip])

        if total_requests >= RATE_LIMIT_MAX_REQUESTS:
            # 触发限流，封禁IP
            blocked_ips[ip] = current_time + RATE_LIMIT_BLOCK_DURATION
            return False, f"请求过于频繁，已被临时封禁{RATE_LIMIT_BLOCK_DURATION}秒"

        # 记录请求
        request_counter[ip].append((current_time, 1))

    return True, ""


def get_rate_limit_status(ip: str) -> Dict:
    """获取IP的限流状态"""
    current_time = time.time()
    redis_client = get_redis_client()
    if redis_client:
        window = int(current_time // RATE_LIMIT_WINDOW)
        rate_key = _redis_key(f"rate:{ip}:{window}")
        blocked_key = _redis_key(f"blocked:{ip}")
        count = int(redis_client.get(rate_key) or 0)
        ttl = redis_client.ttl(blocked_key)
        is_blocked = ttl and ttl > 0
        block_remaining = ttl if is_blocked else 0
        return {
            'ip': ip,
            'requests_in_window': count,
            'max_requests': RATE_LIMIT_MAX_REQUESTS,
            'window_seconds': RATE_LIMIT_WINDOW,
            'is_blocked': bool(is_blocked),
            'block_remaining_seconds': max(0, block_remaining)
        }

    with _lock:
        cutoff = current_time - RATE_LIMIT_WINDOW
        requests = [(t, c) for t, c in request_counter.get(ip, []) if t > cutoff]
        total = sum(c for t, c in requests)

        is_blocked = ip in blocked_ips and current_time < blocked_ips[ip]
        block_remaining = int(blocked_ips.get(ip, 0) - current_time) if is_blocked else 0

    return {
        'ip': ip,
        'requests_in_window': total,
        'max_requests': RATE_LIMIT_MAX_REQUESTS,
        'window_seconds': RATE_LIMIT_WINDOW,
        'is_blocked': is_blocked,
        'block_remaining_seconds': max(0, block_remaining)
    }


# ==================== 防爬虫 ====================

def detect_crawler(user_agent: str, request_path: str, ip: str) -> Tuple[bool, str]:
    """
    检测爬虫行为
    返回: (是否是爬虫, 原因)
    """
    if not user_agent:
        return True, "缺少User-Agent"
    
    user_agent_lower = user_agent.lower()
    
    # 检查已知爬虫UA
    for crawler in CRAWLER_USER_AGENTS:
        if crawler in user_agent_lower:
            return True, f"检测到爬虫特征: {crawler}"
    
    # 检查请求模式
    for pattern in CRAWLER_PATTERNS:
        if re.search(pattern, request_path):
            return True, f"检测到爬虫请求模式"
    
    # 检查请求频率特征（短时间内大量请求同一资源）
    # 这部分由rate_limit处理
    
    return False, ""


def add_crawler_block(ip: str, reason: str, duration: int = 3600):
    """添加爬虫封禁"""
    redis_client = get_redis_client()
    if redis_client:
        redis_client.setex(_redis_key(f"blocked:{ip}"), duration, reason or "crawler")
    with _lock:
        blocked_ips[ip] = time.time() + duration
    
    # 记录到数据库
    try:
        conn = open_security_connection(dict_cursor=True)
        cursor = conn.cursor()
        blocked_until = datetime.now() + timedelta(seconds=duration)
        if is_security_mysql():
            cursor.execute('''
                INSERT INTO blocked_ips (ip_address, reason, blocked_until)
                VALUES (?, ?, ?)
                ON DUPLICATE KEY UPDATE reason = VALUES(reason), blocked_until = VALUES(blocked_until)
            ''', (ip, reason, blocked_until))
        else:
            cursor.execute('''
                INSERT OR REPLACE INTO blocked_ips (ip_address, reason, blocked_until)
                VALUES (?, ?, ?)
            ''', (ip, reason, blocked_until))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[Security] 记录封禁失败: {e}")


# ==================== 登录日志 ====================

def record_login(username: str, ip: str, user_agent: str, success: bool, failure_reason: str = None):
    """记录登录日志"""
    try:
        conn = open_security_connection(dict_cursor=True)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO login_logs (username, ip_address, user_agent, success, failure_reason)
            VALUES (?, ?, ?, ?, ?)
        ''', (username, ip, user_agent, 1 if success else 0, failure_reason))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[Security] 记录登录日志失败: {e}")


def check_login_attempts(ip: str) -> Tuple[bool, str]:
    """
    检查登录尝试次数
    返回: (是否允许登录, 错误信息)
    """
    current_time = time.time()
    redis_client = get_redis_client()
    if redis_client:
        key = _redis_key(f"login_fail:{ip}")
        cutoff = current_time - LOGIN_BLOCK_DURATION
        redis_client.zremrangebyscore(key, 0, cutoff)
        failed_count = redis_client.zcard(key)

        if failed_count >= LOGIN_MAX_ATTEMPTS:
            oldest = redis_client.zrange(key, 0, 0, withscores=True)
            if oldest:
                oldest_time = oldest[0][1]
                remaining = int(LOGIN_BLOCK_DURATION - (current_time - oldest_time))
                if remaining > 0:
                    return False, f"登录尝试次数过多，请在{remaining}秒后重试"
        return True, ""

    with _lock:
        # 清理过期记录
        cutoff = current_time - LOGIN_BLOCK_DURATION
        login_attempts[ip] = [(t, s) for t, s in login_attempts[ip] if t > cutoff]
        
        # 统计失败次数
        failed_count = sum(1 for t, s in login_attempts[ip] if not s)
        
        if failed_count >= LOGIN_MAX_ATTEMPTS:
            oldest_fail = min((t for t, s in login_attempts[ip] if not s), default=current_time)
            remaining = int(LOGIN_BLOCK_DURATION - (current_time - oldest_fail))
            if remaining > 0:
                return False, f"登录尝试次数过多，请在{remaining}秒后重试"
    
    return True, ""


def record_login_attempt(ip: str, success: bool):
    """记录登录尝试"""
    redis_client = get_redis_client()
    if redis_client:
        if not success:
            key = _redis_key(f"login_fail:{ip}")
            member = f"{time.time()}-{uuid.uuid4().hex}"
            redis_client.zadd(key, {member: time.time()})
            redis_client.expire(key, LOGIN_BLOCK_DURATION + 60)
        return

    with _lock:
        login_attempts[ip].append((time.time(), success))


def get_login_logs(username: str = None, limit: int = 100) -> List[Dict]:
    """获取登录日志"""
    try:
        conn = open_security_connection(dict_cursor=True)
        cursor = conn.cursor()
        
        if username:
            cursor.execute('''
                SELECT id, username, ip_address, user_agent, success, failure_reason, created_at
                FROM login_logs WHERE username = ?
                ORDER BY created_at DESC LIMIT ?
            ''', (username, limit))
        else:
            cursor.execute('''
                SELECT id, username, ip_address, user_agent, success, failure_reason, created_at
                FROM login_logs ORDER BY created_at DESC LIMIT ?
            ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [{
            'id': r['id'],
            'username': r['username'],
            'ip_address': r['ip_address'],
            'user_agent': r['user_agent'],
            'success': bool(r['success']),
            'failure_reason': r['failure_reason'],
            'created_at': r['created_at']
        } for r in rows]
    except Exception as e:
        print(f"[Security] 获取登录日志失败: {e}")
        return []


# ==================== 会话管理 ====================

def _cache_session(redis_client, token_hash: str, session: Dict) -> None:
    key = _redis_key(f"session:{token_hash}")
    redis_client.hset(key, mapping=session)
    try:
        expires_at = datetime.fromisoformat(session["expires_at"])
        ttl = int((expires_at - datetime.now()).total_seconds())
        if ttl > 0:
            redis_client.expire(key, ttl)
        else:
            redis_client.delete(key)
    except Exception:
        redis_client.expire(key, SESSION_MAX_AGE)


def create_session(token: str, username: str, ip: str, user_agent: str) -> bool:
    """创建会话"""
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    expires_at = datetime.now() + timedelta(seconds=SESSION_MAX_AGE)
    
    try:
        conn = open_security_connection(dict_cursor=True)
        cursor = conn.cursor()
        
        # 检查用户会话数量
        cursor.execute('SELECT COUNT(*) as count FROM sessions WHERE username = ?', (username,))
        row = cursor.fetchone()
        count = row['count'] if row else 0
        
        if count >= SESSION_MAX_PER_USER:
            # 删除最旧的会话
            cursor.execute('''
                DELETE FROM sessions WHERE id IN (
                    SELECT id FROM (
                        SELECT id FROM sessions WHERE username = ?
                        ORDER BY last_active ASC LIMIT ?
                    ) AS old_sessions
                )
            ''', (username, count - SESSION_MAX_PER_USER + 1))
        
        # 创建新会话
        cursor.execute('''
            INSERT INTO sessions (token_hash, username, ip_address, user_agent, expires_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (token_hash, username, ip, user_agent, expires_at.isoformat()))
        
        conn.commit()
        conn.close()
        
        session = {
            'username': username,
            'ip': ip,
            'created_at': datetime.now().isoformat(),
            'expires_at': expires_at.isoformat()
        }

        redis_client = get_redis_client()
        if redis_client:
            _cache_session(redis_client, token_hash, session)
        else:
            # 内存缓存
            with _lock:
                active_sessions[token_hash] = session
        
        return True
    except Exception as e:
        print(f"[Security] 创建会话失败: {e}")
        return False


def validate_session(token: str) -> Optional[Dict]:
    """验证会话"""
    token_hash = hashlib.sha256(token.encode()).hexdigest()

    redis_client = get_redis_client()
    if redis_client:
        key = _redis_key(f"session:{token_hash}")
        cached = redis_client.hgetall(key)
        if cached:
            try:
                if datetime.fromisoformat(cached['expires_at']) > datetime.now():
                    return cached
            except Exception:
                return cached
        redis_client.delete(key)
    else:
        # 先检查内存缓存
        with _lock:
            if token_hash in active_sessions:
                session = active_sessions[token_hash]
                if datetime.fromisoformat(session['expires_at']) > datetime.now():
                    return session
                else:
                    del active_sessions[token_hash]
    
    # 检查数据库
    try:
        conn = open_security_connection(dict_cursor=True)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT username, ip_address, created_at, expires_at
            FROM sessions WHERE token_hash = ? AND expires_at > CURRENT_TIMESTAMP
        ''', (token_hash,))
        row = cursor.fetchone()
        
        if row:
            # 更新最后活跃时间
            cursor.execute('''
                UPDATE sessions SET last_active = CURRENT_TIMESTAMP WHERE token_hash = ?
            ''', (token_hash,))
            conn.commit()
            conn.close()
            
            session = {
                'username': row['username'],
                'ip': row['ip_address'],
                'created_at': row['created_at'],
                'expires_at': row['expires_at']
            }
            
            # 更新缓存
            if redis_client:
                _cache_session(redis_client, token_hash, session)
            else:
                with _lock:
                    active_sessions[token_hash] = session
            
            return session
        
        conn.close()
    except Exception as e:
        print(f"[Security] 验证会话失败: {e}")
    
    return None


def revoke_session(token: str) -> bool:
    """撤销会话"""
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    redis_client = get_redis_client()
    if redis_client:
        redis_client.delete(_redis_key(f"session:{token_hash}"))
    else:
        with _lock:
            if token_hash in active_sessions:
                del active_sessions[token_hash]
    
    try:
        conn = open_security_connection(dict_cursor=True)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM sessions WHERE token_hash = ?', (token_hash,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"[Security] 撤销会话失败: {e}")
        return False


def get_user_sessions(username: str) -> List[Dict]:
    """获取用户所有会话"""
    try:
        conn = open_security_connection(dict_cursor=True)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, ip_address, user_agent, created_at, last_active, expires_at
            FROM sessions WHERE username = ? AND expires_at > CURRENT_TIMESTAMP
            ORDER BY last_active DESC
        ''', (username,))
        rows = cursor.fetchall()
        conn.close()
        
        return [{
            'id': r['id'],
            'ip_address': r['ip_address'],
            'user_agent': r['user_agent'],
            'created_at': r['created_at'],
            'last_active': r['last_active'],
            'expires_at': r['expires_at']
        } for r in rows]
    except Exception as e:
        print(f"[Security] 获取用户会话失败: {e}")
        return []


def revoke_all_user_sessions(username: str, except_token: str = None) -> int:
    """撤销用户所有会话"""
    try:
        conn = open_security_connection(dict_cursor=True)
        cursor = conn.cursor()
        
        if except_token:
            except_hash = hashlib.sha256(except_token.encode()).hexdigest()
            cursor.execute('''
                DELETE FROM sessions WHERE username = ? AND token_hash != ?
            ''', (username, except_hash))
        else:
            cursor.execute('DELETE FROM sessions WHERE username = ?', (username,))
        
        count = cursor.rowcount
        conn.commit()
        conn.close()
        
        redis_client = get_redis_client()
        if redis_client:
            pattern = _redis_key("session:*")
            prefix = _redis_key("session:")
            except_hash = hashlib.sha256(except_token.encode()).hexdigest() if except_token else None
            for key in redis_client.scan_iter(match=pattern):
                data = redis_client.hgetall(key)
                if not data:
                    continue
                if data.get("username") != username:
                    continue
                token_hash = key[len(prefix):] if key.startswith(prefix) else key
                if except_hash and token_hash == except_hash:
                    continue
                redis_client.delete(key)
        else:
            # 清理内存缓存
            with _lock:
                to_delete = [k for k, v in active_sessions.items()
                            if v['username'] == username and
                            (not except_token or k != hashlib.sha256(except_token.encode()).hexdigest())]
                for k in to_delete:
                    del active_sessions[k]
        
        return count
    except Exception as e:
        print(f"[Security] 撤销用户会话失败: {e}")
        return 0


# ==================== 密码策略 ====================

def validate_password(password: str) -> Tuple[bool, List[str]]:
    """
    验证密码是否符合策略
    返回: (是否有效, 错误列表)
    """
    errors = []
    
    if len(password) < PASSWORD_MIN_LENGTH:
        errors.append(f"密码长度至少{PASSWORD_MIN_LENGTH}位")
    
    if PASSWORD_REQUIRE_UPPERCASE and not re.search(r'[A-Z]', password):
        errors.append("密码必须包含大写字母")
    
    if PASSWORD_REQUIRE_LOWERCASE and not re.search(r'[a-z]', password):
        errors.append("密码必须包含小写字母")
    
    if PASSWORD_REQUIRE_DIGIT and not re.search(r'\d', password):
        errors.append("密码必须包含数字")
    
    if PASSWORD_REQUIRE_SPECIAL and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        errors.append("密码必须包含特殊字符")
    
    return len(errors) == 0, errors


def get_password_policy() -> Dict:
    """获取密码策略"""
    return {
        'min_length': PASSWORD_MIN_LENGTH,
        'require_uppercase': PASSWORD_REQUIRE_UPPERCASE,
        'require_lowercase': PASSWORD_REQUIRE_LOWERCASE,
        'require_digit': PASSWORD_REQUIRE_DIGIT,
        'require_special': PASSWORD_REQUIRE_SPECIAL
    }


# ==================== 审计日志 ====================

def record_audit_log(username: str, action: str, resource: str = None, 
                     resource_id: int = None, old_value: str = None, 
                     new_value: str = None, ip: str = None):
    """记录审计日志"""
    try:
        conn = open_security_connection(dict_cursor=True)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO audit_logs (username, action, resource, resource_id, old_value, new_value, ip_address)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (username, action, resource, resource_id, old_value, new_value, ip))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[Security] 记录审计日志失败: {e}")


def get_audit_logs(username: str = None, action: str = None, limit: int = 100) -> List[Dict]:
    """获取审计日志"""
    try:
        conn = open_security_connection(dict_cursor=True)
        cursor = conn.cursor()
        
        query = 'SELECT id, username, action, resource, resource_id, old_value, new_value, ip_address, created_at FROM audit_logs WHERE 1=1'
        params = []
        
        if username:
            query += ' AND username = ?'
            params.append(username)
        if action:
            query += ' AND action = ?'
            params.append(action)
        
        query += ' ORDER BY created_at DESC LIMIT ?'
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        return [{
            'id': r['id'],
            'username': r['username'],
            'action': r['action'],
            'resource': r['resource'],
            'resource_id': r['resource_id'],
            'old_value': r['old_value'],
            'new_value': r['new_value'],
            'ip_address': r['ip_address'],
            'created_at': r['created_at']
        } for r in rows]
    except Exception as e:
        print(f"[Security] 获取审计日志失败: {e}")
        return []


# ==================== 数据历史 ====================

def record_data_history(record_id: int, action: str, changes: Dict = None, username: str = None):
    """记录数据修改历史"""
    try:
        conn = open_security_connection(dict_cursor=True)
        cursor = conn.cursor()
        
        if action == 'DELETE':
            # 删除时记录整条记录
            cursor.execute('''
                INSERT INTO data_history (record_id, action, old_value, username)
                VALUES (?, ?, ?, ?)
            ''', (record_id, action, str(changes) if changes else None, username))
        elif action == 'CREATE':
            cursor.execute('''
                INSERT INTO data_history (record_id, action, new_value, username)
                VALUES (?, ?, ?, ?)
            ''', (record_id, action, str(changes) if changes else None, username))
        elif action == 'UPDATE' and changes:
            for field, (old_val, new_val) in changes.items():
                cursor.execute('''
                    INSERT INTO data_history (record_id, action, field_name, old_value, new_value, username)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (record_id, action, field, str(old_val), str(new_val), username))
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[Security] 记录数据历史失败: {e}")


def get_data_history(record_id: int = None, action: str = None, username: str = None, limit: int = 100) -> List[Dict]:
    """获取数据历史"""
    try:
        conn = open_security_connection(dict_cursor=True)
        cursor = conn.cursor()

        query = '''
            SELECT id, record_id, action, field_name, old_value, new_value, username, created_at
            FROM data_history WHERE 1=1
        '''
        params = []
        if record_id:
            query += ' AND record_id = ?'
            params.append(record_id)
        if action:
            query += ' AND action = ?'
            params.append(action)
        if username:
            query += ' AND username = ?'
            params.append(username)

        query += ' ORDER BY created_at DESC LIMIT ?'
        params.append(limit)

        cursor.execute(query, params)
        
        rows = cursor.fetchall()
        conn.close()
        
        return [{
            'id': r['id'],
            'record_id': r['record_id'],
            'action': r['action'],
            'field_name': r['field_name'],
            'old_value': r['old_value'],
            'new_value': r['new_value'],
            'username': r['username'],
            'created_at': r['created_at']
        } for r in rows]
    except Exception as e:
        print(f"[Security] 获取数据历史失败: {e}")
        return []


# ==================== 初始化 ====================

def init_security():
    """初始化安全模块"""
    init_security_db()
    print("[Security] 安全模块初始化完成")
