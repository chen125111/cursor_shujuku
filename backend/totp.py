"""
TOTP 两步验证模块
基于 RFC 6238 实现
"""

import hmac
import hashlib
import struct
import time
import base64
import os
from typing import Tuple

from backend.db import is_security_mysql, open_security_connection

# TOTP 配置
TOTP_DIGITS = 6  # 验证码位数
TOTP_INTERVAL = 30  # 时间间隔（秒）
TOTP_ISSUER = "GasMixtureSystem"  # 发行者名称


def generate_secret(length: int = 32) -> str:
    """生成随机密钥"""
    # 生成随机字节
    random_bytes = os.urandom(length)
    # Base32 编码
    secret = base64.b32encode(random_bytes).decode('utf-8').rstrip('=')
    return secret


def get_totp_token(secret: str, timestamp: int = None) -> str:
    """
    生成 TOTP 验证码
    """
    if timestamp is None:
        timestamp = int(time.time())
    
    # 计算时间步长
    time_step = timestamp // TOTP_INTERVAL
    
    # 解码密钥
    # 补齐 Base32 填充
    padding = 8 - (len(secret) % 8)
    if padding != 8:
        secret += '=' * padding
    
    try:
        key = base64.b32decode(secret.upper())
    except Exception:
        return ""
    
    # 将时间步长转换为字节
    time_bytes = struct.pack('>Q', time_step)
    
    # HMAC-SHA1
    hmac_hash = hmac.new(key, time_bytes, hashlib.sha1).digest()
    
    # 动态截取
    offset = hmac_hash[-1] & 0x0F
    truncated = struct.unpack('>I', hmac_hash[offset:offset + 4])[0]
    truncated &= 0x7FFFFFFF
    
    # 取模得到指定位数的验证码
    code = truncated % (10 ** TOTP_DIGITS)
    
    return str(code).zfill(TOTP_DIGITS)


def verify_totp(secret: str, code: str, window: int = 1) -> bool:
    """
    验证 TOTP 验证码
    window: 允许的时间窗口偏移（前后各 window 个时间步长）
    """
    if not code or len(code) != TOTP_DIGITS:
        return False
    
    current_time = int(time.time())
    
    # 检查当前时间及前后 window 个时间步长
    for offset in range(-window, window + 1):
        check_time = current_time + (offset * TOTP_INTERVAL)
        expected = get_totp_token(secret, check_time)
        if expected and hmac.compare_digest(expected, code):
            return True
    
    return False


def get_totp_uri(secret: str, username: str) -> str:
    """
    生成 TOTP URI（用于二维码）
    格式: otpauth://totp/{issuer}:{username}?secret={secret}&issuer={issuer}&digits={digits}&period={period}
    """
    return f"otpauth://totp/{TOTP_ISSUER}:{username}?secret={secret}&issuer={TOTP_ISSUER}&digits={TOTP_DIGITS}&period={TOTP_INTERVAL}"


# ==================== 数据库操作 ====================

def init_totp_table():
    """初始化 TOTP 表"""
    id_column = "BIGINT PRIMARY KEY AUTO_INCREMENT" if is_security_mysql() else "INTEGER PRIMARY KEY AUTOINCREMENT"
    username_type = "VARCHAR(64)" if is_security_mysql() else "TEXT"
    secret_type = "VARCHAR(64)" if is_security_mysql() else "TEXT"
    conn = open_security_connection(dict_cursor=True)
    cursor = conn.cursor()
    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS user_totp (
            id {id_column},
            username {username_type} UNIQUE NOT NULL,
            secret {secret_type} NOT NULL,
            enabled INTEGER DEFAULT 0,
            backup_codes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_used TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()


def setup_totp(username: str) -> Tuple[str, str]:
    """
    为用户设置 TOTP
    返回: (secret, uri)
    """
    secret = generate_secret()
    uri = get_totp_uri(secret, username)
    
    # 生成备用码
    backup_codes = [generate_secret(8)[:8] for _ in range(10)]
    backup_codes_str = ','.join(backup_codes)
    
    conn = open_security_connection(dict_cursor=True)
    cursor = conn.cursor()
    
    # 检查是否已存在
    cursor.execute('SELECT id FROM user_totp WHERE username = ?', (username,))
    if cursor.fetchone():
        cursor.execute('''
            UPDATE user_totp SET secret = ?, enabled = 0, backup_codes = ?
            WHERE username = ?
        ''', (secret, backup_codes_str, username))
    else:
        cursor.execute('''
            INSERT INTO user_totp (username, secret, backup_codes)
            VALUES (?, ?, ?)
        ''', (username, secret, backup_codes_str))
    
    conn.commit()
    conn.close()
    
    return secret, uri


def enable_totp(username: str, code: str) -> bool:
    """启用 TOTP（需要验证码确认）"""
    conn = open_security_connection(dict_cursor=True)
    cursor = conn.cursor()
    
    cursor.execute('SELECT secret FROM user_totp WHERE username = ?', (username,))
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        return False
    
    secret = row['secret']
    
    if verify_totp(secret, code):
        cursor.execute('UPDATE user_totp SET enabled = 1 WHERE username = ?', (username,))
        conn.commit()
        conn.close()
        return True
    
    conn.close()
    return False


def disable_totp(username: str) -> bool:
    """禁用 TOTP"""
    conn = open_security_connection(dict_cursor=True)
    cursor = conn.cursor()
    cursor.execute('UPDATE user_totp SET enabled = 0 WHERE username = ?', (username,))
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0


def is_totp_enabled(username: str) -> bool:
    """检查用户是否启用了 TOTP"""
    conn = open_security_connection(dict_cursor=True)
    cursor = conn.cursor()
    cursor.execute('SELECT enabled FROM user_totp WHERE username = ?', (username,))
    row = cursor.fetchone()
    conn.close()
    return bool(row and row['enabled'])


def verify_user_totp(username: str, code: str) -> bool:
    """验证用户的 TOTP 验证码"""
    conn = open_security_connection(dict_cursor=True)
    cursor = conn.cursor()
    
    cursor.execute('SELECT secret, backup_codes FROM user_totp WHERE username = ? AND enabled = 1', (username,))
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        return False
    
    secret = row['secret']
    backup_codes_str = row['backup_codes']
    
    # 先尝试正常验证码
    if verify_totp(secret, code):
        cursor.execute('UPDATE user_totp SET last_used = CURRENT_TIMESTAMP WHERE username = ?', (username,))
        conn.commit()
        conn.close()
        return True
    
    # 尝试备用码
    if backup_codes_str:
        backup_codes = backup_codes_str.split(',')
        if code in backup_codes:
            # 使用后删除备用码
            backup_codes.remove(code)
            cursor.execute('UPDATE user_totp SET backup_codes = ?, last_used = CURRENT_TIMESTAMP WHERE username = ?',
                          (','.join(backup_codes), username))
            conn.commit()
            conn.close()
            return True
    
    conn.close()
    return False


def get_totp_status(username: str) -> dict:
    """获取用户的 TOTP 状态"""
    conn = open_security_connection(dict_cursor=True)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT enabled, created_at, last_used, backup_codes
        FROM user_totp WHERE username = ?
    ''', (username,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return {
            'configured': False,
            'enabled': False
        }
    
    backup_count = len(row['backup_codes'].split(',')) if row['backup_codes'] else 0
    
    return {
        'configured': True,
        'enabled': bool(row['enabled']),
        'created_at': row['created_at'],
        'last_used': row['last_used'],
        'backup_codes_remaining': backup_count
    }


def regenerate_backup_codes(username: str) -> list:
    """重新生成备用码"""
    backup_codes = [generate_secret(8)[:8] for _ in range(10)]
    backup_codes_str = ','.join(backup_codes)
    
    conn = open_security_connection(dict_cursor=True)
    cursor = conn.cursor()
    cursor.execute('UPDATE user_totp SET backup_codes = ? WHERE username = ?',
                  (backup_codes_str, username))
    conn.commit()
    conn.close()
    
    return backup_codes


# 初始化
init_totp_table()

