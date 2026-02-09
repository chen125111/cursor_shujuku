"""
自动备份模块 - 数据库定时备份

说明：
- 主要针对 SQLite 文件数据库提供备份/恢复能力
- 当切换到 MySQL（托管数据库）时，本模块会自动降级：仅返回提示，不执行文件级备份
"""

import os
import shutil
import sqlite3
import threading
import time
from datetime import datetime
from typing import List, Optional

from backend.config import get_backup_dir, get_database_path
from backend.db import is_mysql

# ==================== 配置 ====================

def _backup_enabled() -> bool:
    raw = os.getenv("BACKUP_ENABLED")
    if raw is None:
        return True
    return raw.strip().lower() not in ("0", "false", "no", "off", "")


def _backup_dir() -> str:
    return get_backup_dir()


def _database_path() -> str:
    return get_database_path()

# 保留备份数量
MAX_BACKUPS = 10

# 自动备份间隔（秒）- 默认6小时
BACKUP_INTERVAL = 6 * 60 * 60

# 备份线程
_backup_thread: Optional[threading.Thread] = None
_backup_running = False


# ==================== 备份功能 ====================

def is_backup_supported() -> bool:
    """
    判断当前数据库模式是否支持文件级备份。

    Returns:
        当使用 SQLite 且 BACKUP_ENABLED 未显式关闭时返回 True；否则 False。
    """
    return _backup_enabled() and (not is_mysql())


def ensure_backup_dir():
    """
    确保备份目录存在（不存在则创建）。

    Notes:
        - 若当前为 MySQL 模式或 BACKUP_ENABLED 禁用，会直接返回，不做任何操作。
    """
    if not is_backup_supported():
        return
    backup_dir = _backup_dir()
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
        print(f"[Backup] 创建备份目录: {backup_dir}")


def create_backup(manual: bool = False) -> Optional[str]:
    """
    创建数据库备份

    Args:
        manual: 是否为手动备份（影响备份文件名中的类型标识）

    Returns:
        备份文件路径；在 MySQL 模式或失败时返回 None。
    """
    try:
        if not is_backup_supported():
            print("[Backup] MySQL 使用托管备份，跳过文件备份")
            return None
        ensure_backup_dir()
        
        # 检查源数据库是否存在
        db_path = _database_path()
        if not os.path.exists(db_path):
            print("[Backup] 数据库文件不存在")
            return None
        
        # 生成备份文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_type = "manual" if manual else "auto"
        backup_filename = f"gas_data_{backup_type}_{timestamp}.db"
        backup_path = os.path.join(_backup_dir(), backup_filename)
        
        # 使用 SQLite 的备份 API 进行安全备份
        source_conn = sqlite3.connect(db_path)
        backup_conn = sqlite3.connect(backup_path)
        
        source_conn.backup(backup_conn)
        
        source_conn.close()
        backup_conn.close()
        
        # 获取备份文件大小
        backup_size = os.path.getsize(backup_path)
        size_str = format_size(backup_size)
        
        print(f"[Backup] 备份成功: {backup_filename} ({size_str})")
        
        # 清理旧备份
        cleanup_old_backups()
        
        return backup_path
        
    except Exception as e:
        print(f"[Backup] 备份失败: {e}")
        return None


def restore_backup(backup_filename: str) -> bool:
    """
    从备份恢复数据库

    Args:
        backup_filename: 备份文件名（位于备份目录下）

    Returns:
        是否恢复成功。

    Notes:
        - 恢复前会先对当前数据库执行一次手动备份，避免误操作导致不可回滚。
    """
    try:
        if not is_backup_supported():
            print("[Backup] MySQL 使用托管备份，无法从文件恢复")
            return False
        backup_path = os.path.join(_backup_dir(), backup_filename)
        
        if not os.path.exists(backup_path):
            print(f"[Backup] 备份文件不存在: {backup_filename}")
            return False
        
        # 先备份当前数据库
        create_backup(manual=True)
        
        # 恢复备份
        shutil.copy2(backup_path, _database_path())
        
        print(f"[Backup] 恢复成功: {backup_filename}")
        return True
        
    except Exception as e:
        print(f"[Backup] 恢复失败: {e}")
        return False


def list_backups() -> List[dict]:
    """
    列出所有备份文件

    Returns:
        备份信息列表（按创建时间倒序），每项包含 filename/size/created_at/type 等字段。
    """
    if not is_backup_supported():
        return []
    ensure_backup_dir()
    
    backup_dir = _backup_dir()
    backups = []
    for filename in os.listdir(backup_dir):
        if filename.endswith('.db'):
            filepath = os.path.join(backup_dir, filename)
            stat = os.stat(filepath)
            
            # 解析备份类型和时间
            parts = filename.replace('.db', '').split('_')
            backup_type = parts[2] if len(parts) > 2 else 'unknown'
            
            backups.append({
                'filename': filename,
                'size': stat.st_size,
                'size_formatted': format_size(stat.st_size),
                'created_at': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'type': backup_type
            })
    
    # 按时间倒序排列
    backups.sort(key=lambda x: x['created_at'], reverse=True)
    return backups


def delete_backup(backup_filename: str) -> bool:
    """
    删除指定备份

    Args:
        backup_filename: 备份文件名

    Returns:
        是否删除成功。
    """
    try:
        if not is_backup_supported():
            return False
        backup_path = os.path.join(_backup_dir(), backup_filename)
        if os.path.exists(backup_path):
            os.remove(backup_path)
            print(f"[Backup] 删除备份: {backup_filename}")
            return True
        return False
    except Exception as e:
        print(f"[Backup] 删除失败: {e}")
        return False


def cleanup_old_backups():
    """
    清理超出数量限制的旧备份

    Notes:
        - 会保留最近的 `MAX_BACKUPS` 个备份文件，多余的从最旧开始删除。
    """
    if not is_backup_supported():
        return
    backups = list_backups()
    
    if len(backups) > MAX_BACKUPS:
        # 删除最旧的备份
        for backup in backups[MAX_BACKUPS:]:
            delete_backup(backup['filename'])


def format_size(size_bytes: int) -> str:
    """
    将字节数转换为更友好的字符串表示。

    Args:
        size_bytes: 文件大小（字节）

    Returns:
        格式化后的字符串（B/KB/MB/GB/TB）。
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


# ==================== 自动备份 ====================

def _backup_worker():
    """
    自动备份工作线程。

    Notes:
        - 线程以秒为粒度睡眠，便于在停止时更快退出。
        - 达到间隔后触发一次自动备份。
    """
    global _backup_running
    
    print(f"[Backup] 自动备份已启动，间隔: {BACKUP_INTERVAL // 3600} 小时")
    
    while _backup_running:
        # 等待指定间隔
        for _ in range(BACKUP_INTERVAL):
            if not _backup_running:
                break
            time.sleep(1)
        
        if _backup_running:
            create_backup(manual=False)


def start_auto_backup():
    """
    启动自动备份线程，并在启动时立即执行一次自动备份。

    Notes:
        - 若已在运行，会直接返回。
    """
    global _backup_thread, _backup_running
    
    if _backup_running:
        print("[Backup] 自动备份已在运行")
        return
    
    _backup_running = True
    _backup_thread = threading.Thread(target=_backup_worker, daemon=True)
    _backup_thread.start()
    
    # 启动时立即创建一次备份
    create_backup(manual=False)


def stop_auto_backup():
    """
    停止自动备份线程（通过标志位让工作线程退出）。
    """
    global _backup_running
    _backup_running = False
    print("[Backup] 自动备份已停止")


def get_backup_status() -> dict:
    """
    获取备份系统状态摘要（用于管理后台展示）。

    Returns:
        状态字典，包含是否启用自动备份、备份数量、总大小、最后备份时间等。
        MySQL 模式会返回 `managed_by=rds` 等提示字段。
        BACKUP_ENABLED 关闭时会返回 `managed_by=disabled`。
    """
    if not _backup_enabled():
        return {
            "auto_backup_enabled": False,
            "backup_interval_hours": 0,
            "backup_count": 0,
            "total_size": format_size(0),
            "max_backups": MAX_BACKUPS,
            "backup_dir": _backup_dir(),
            "last_backup": None,
            "managed_by": "disabled",
        }
    if not is_backup_supported():
        return {
            'auto_backup_enabled': False,
            'backup_interval_hours': 0,
            'backup_count': 0,
            'total_size': format_size(0),
            'max_backups': MAX_BACKUPS,
            'backup_dir': _backup_dir(),
            'last_backup': None,
            'managed_by': 'rds'
        }
    backups = list_backups()
    total_size = sum(b['size'] for b in backups)
    
    return {
        'auto_backup_enabled': _backup_running,
        'backup_interval_hours': BACKUP_INTERVAL // 3600,
        'backup_count': len(backups),
        'total_size': format_size(total_size),
        'max_backups': MAX_BACKUPS,
        'backup_dir': _backup_dir(),
        'last_backup': backups[0]['created_at'] if backups else None
    }


# ==================== 初始化 ====================

def init_backup_system():
    """
    初始化备份系统：确保备份目录存在并启动自动备份。

    Notes:
        - MySQL 模式下不会启用文件备份。
    """
    if not _backup_enabled():
        print("[Backup] 备份已通过 BACKUP_ENABLED 禁用")
        return
    if not is_backup_supported():
        print("[Backup] MySQL 使用托管备份，自动备份已跳过")
        return
    ensure_backup_dir()
    start_auto_backup()
    print("[Backup] 备份系统初始化完成")

