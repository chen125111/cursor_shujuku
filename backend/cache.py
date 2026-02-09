"""
Redis缓存模块
为数据库查询和API响应提供缓存功能
"""

import hashlib
import inspect
import json
import logging
import os
import pickle
import time
from functools import wraps
from typing import Any, Callable, Optional

import redis

# 配置日志
logger = logging.getLogger(__name__)


def _env_flag(name: str, default: bool = True) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() not in ("0", "false", "no", "off", "")


def _cache_enabled() -> bool:
    return _env_flag("CACHE_ENABLED", True)


def _redis_url() -> str:
    return os.getenv("REDIS_URL", "").strip()


class RedisCache:
    """Redis缓存管理器"""
    
    def __init__(self, host: str = 'localhost', port: int = 6379, 
                 db: int = 0, password: Optional[str] = None,
                 default_ttl: int = 300):
        """
        初始化Redis连接
        
        Args:
            host: Redis主机
            port: Redis端口
            db: Redis数据库编号
            password: Redis密码
            default_ttl: 默认缓存时间（秒）
        """
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.default_ttl = default_ttl
        self._client = None
        self._connected = False
        
    def connect(self) -> bool:
        """连接Redis服务器"""
        if not _cache_enabled():
            self._connected = False
            self._client = None
            logger.info("缓存已通过 CACHE_ENABLED 禁用")
            return False

        try:
            url = _redis_url()
            if url:
                self._client = redis.Redis.from_url(
                    url,
                    decode_responses=False,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True,
                )
            else:
                self._client = redis.Redis(
                    host=self.host,
                    port=self.port,
                    db=self.db,
                    password=self.password,
                    decode_responses=False,  # 不自动解码，支持二进制数据
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True,
                )
            # 测试连接
            self._client.ping()
            self._connected = True
            logger.info("Redis连接成功")
            return True
        except Exception as e:
            logger.error(f"Redis连接失败: {e}")
            self._connected = False
            return False
    
    def is_connected(self) -> bool:
        """检查Redis连接状态"""
        if not self._connected or not self._client:
            return False
        try:
            self._client.ping()
            return True
        except Exception:
            self._connected = False
            return False
    
    def get_client(self) -> Optional[redis.Redis]:
        """获取Redis客户端实例"""
        if not self.is_connected():
            if not self.connect():
                return None
        return self._client
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        设置缓存
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒），None使用默认值
            
        Returns:
            是否设置成功
        """
        client = self.get_client()
        if not client:
            return False
        
        try:
            # 序列化值
            if isinstance(value, (str, int, float, bool, bytes)):
                serialized = value
            else:
                serialized = pickle.dumps(value)
            
            ttl = ttl if ttl is not None else self.default_ttl
            result = client.setex(key, ttl, serialized)
            return bool(result)
        except Exception as e:
            logger.error(f"设置缓存失败: {e}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取缓存
        
        Args:
            key: 缓存键
            default: 缓存不存在时的默认值
            
        Returns:
            缓存值或默认值
        """
        client = self.get_client()
        if not client:
            return default
        
        try:
            value = client.get(key)
            if value is None:
                return default
            
            # 反序列化值
            try:
                # 尝试JSON解码
                return json.loads(value.decode('utf-8'))
            except Exception:
                try:
                    # 尝试pickle解码
                    return pickle.loads(value)
                except Exception:
                    # 返回原始字节
                    return value.decode('utf-8') if isinstance(value, bytes) else value
        except Exception as e:
            logger.error(f"获取缓存失败: {e}")
            return default
    
    def delete(self, key: str) -> bool:
        """删除缓存"""
        client = self.get_client()
        if not client:
            return False
        
        try:
            result = client.delete(key)
            return bool(result)
        except Exception as e:
            logger.error(f"删除缓存失败: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """检查缓存是否存在"""
        client = self.get_client()
        if not client:
            return False
        
        try:
            return bool(client.exists(key))
        except Exception as e:
            logger.error(f"检查缓存失败: {e}")
            return False
    
    def clear_pattern(self, pattern: str) -> int:
        """
        清除匹配模式的缓存
        
        Args:
            pattern: Redis模式（如 "cache:*"）
            
        Returns:
            删除的键数量
        """
        client = self.get_client()
        if not client:
            return 0
        
        try:
            deleted = 0
            batch: list[bytes] = []
            for key in client.scan_iter(match=pattern, count=1000):
                batch.append(key)
                if len(batch) >= 500:
                    deleted += int(client.delete(*batch))
                    batch.clear()
            if batch:
                deleted += int(client.delete(*batch))
            return deleted
        except Exception as e:
            logger.error(f"清除模式缓存失败: {e}")
            return 0
    
    def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """递增计数器"""
        client = self.get_client()
        if not client:
            return None
        
        try:
            return client.incrby(key, amount)
        except Exception as e:
            logger.error(f"递增计数器失败: {e}")
            return None
    
    def get_stats(self) -> dict:
        """获取缓存统计信息"""
        client = self.get_client()
        if not client:
            return {"connected": False}
        
        try:
            info = client.info()
            return {
                "connected": True,
                "used_memory": info.get('used_memory_human', 'N/A'),
                "connected_clients": info.get('connected_clients', 0),
                "total_commands_processed": info.get('total_commands_processed', 0),
                "keyspace_hits": info.get('keyspace_hits', 0),
                "keyspace_misses": info.get('keyspace_misses', 0),
                "hit_rate": info.get('keyspace_hits', 0) / max(1, info.get('keyspace_hits', 0) + info.get('keyspace_misses', 0))
            }
        except Exception as e:
            logger.error(f"获取缓存统计失败: {e}")
            return {"connected": False, "error": str(e)}


def cache_key_generator(*args, **kwargs) -> str:
    """
    生成缓存键
    
    Args:
        *args: 位置参数
        **kwargs: 关键字参数
        
    Returns:
        缓存键字符串
    """
    # 创建参数的字符串表示
    args_str = str(args)
    kwargs_str = str(sorted(kwargs.items()))
    
    # 生成MD5哈希作为键
    key_data = f"{args_str}:{kwargs_str}".encode('utf-8')
    return hashlib.md5(key_data).hexdigest()


def cached(ttl: int = 300, key_prefix: str = "func"):
    """
    缓存装饰器
    
    Args:
        ttl: 缓存时间（秒）
        key_prefix: 缓存键前缀
        
    Returns:
        装饰器函数
    """
    def decorator(func: Callable):
        missing = object()

        def _build_key(args: tuple[object, ...], kwargs: dict[str, object]) -> str:
            digest = cache_key_generator(*args, **kwargs)
            # 统一以 "cache:" 开头，便于按前缀清理
            return f"cache:{key_prefix}:{func.__module__}:{func.__name__}:{digest}"

        if inspect.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                cache = get_cache()
                if not cache or not cache.is_connected():
                    return await func(*args, **kwargs)

                cache_key = _build_key(args, kwargs)
                cached_result = cache.get(cache_key, default=missing)
                if cached_result is not missing:
                    logger.debug(f"缓存命中: {cache_key}")
                    return cached_result

                logger.debug(f"缓存未命中: {cache_key}")
                result = await func(*args, **kwargs)
                cache.set(cache_key, result, ttl)
                return result

            return async_wrapper

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            cache = get_cache()
            if not cache or not cache.is_connected():
                return func(*args, **kwargs)

            cache_key = _build_key(args, kwargs)
            cached_result = cache.get(cache_key, default=missing)
            if cached_result is not missing:
                logger.debug(f"缓存命中: {cache_key}")
                return cached_result

            logger.debug(f"缓存未命中: {cache_key}")
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            return result

        return sync_wrapper
    return decorator


def invalidate_cache(pattern: str = None):
    """
    缓存失效装饰器
    
    Args:
        pattern: 要清除的缓存模式，None表示自动生成
        
    Returns:
        装饰器函数
    """
    def decorator(func: Callable):
        def _invalidate() -> None:
            cache = get_cache()
            if cache and cache.is_connected():
                if pattern:
                    cache.clear_pattern(pattern)
                else:
                    cache.clear_pattern("cache:*")

        if inspect.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                result = await func(*args, **kwargs)
                _invalidate()
                return result

            return async_wrapper

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            _invalidate()
            return result

        return sync_wrapper
    return decorator


# 全局缓存实例
_cache_instance: Optional[RedisCache] = None


def init_cache(host: str = 'localhost', port: int = 6379, 
               db: int = 0, password: Optional[str] = None,
               default_ttl: int = 300) -> RedisCache:
    """
    初始化全局缓存实例
    
    Returns:
        RedisCache实例
    """
    global _cache_instance
    if _cache_instance is None:
        host = os.getenv("REDIS_HOST", host)
        port = int(os.getenv("REDIS_PORT", str(port)))
        db = int(os.getenv("REDIS_DB", str(db)))
        password = os.getenv("REDIS_PASSWORD") or password
        default_ttl = int(os.getenv("CACHE_DEFAULT_TTL", str(default_ttl)))

        _cache_instance = RedisCache(
            host=host, port=port, db=db, 
            password=password, default_ttl=default_ttl
        )
        _cache_instance.connect()
    return _cache_instance


def get_cache() -> Optional[RedisCache]:
    """获取全局缓存实例"""
    global _cache_instance
    if _cache_instance is None:
        # 尝试使用默认配置初始化
        _cache_instance = init_cache()
    return _cache_instance


def clear_cache() -> bool:
    """清除所有缓存"""
    cache = get_cache()
    if cache and cache.is_connected():
        return cache.clear_pattern("cache:*") > 0
    return False


# 测试函数
if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(level=logging.INFO)
    
    # 初始化缓存
    cache = init_cache()
    
    if cache.is_connected():
        print("Redis缓存测试:")
        
        # 测试基本操作
        cache.set("test:string", "Hello Redis")
        print(f"获取字符串: {cache.get('test:string')}")
        
        cache.set("test:dict", {"name": "test", "value": 123})
        print(f"获取字典: {cache.get('test:dict')}")
        
        cache.set("test:list", [1, 2, 3, 4, 5])
        print(f"获取列表: {cache.get('test:list')}")
        
        # 测试装饰器
        @cached(ttl=60)
        def expensive_operation(x: int, y: int) -> int:
            print(f"执行昂贵操作: {x} + {y}")
            time.sleep(0.1)  # 模拟耗时操作
            return x + y
        
        print("\n缓存装饰器测试:")
        print(f"第一次调用: {expensive_operation(10, 20)}")
        print(f"第二次调用（应该从缓存获取）: {expensive_operation(10, 20)}")
        print(f"不同参数调用: {expensive_operation(30, 40)}")
        
        # 获取统计信息
        stats = cache.get_stats()
        print(f"\n缓存统计: {stats}")
    else:
        print("Redis未连接，缓存功能不可用")