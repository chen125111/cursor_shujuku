"""
Redis缓存模块
为数据库查询和API响应提供缓存功能
"""

import hashlib
import inspect
import json
import logging
import os
import time
import fnmatch
import threading
from collections import OrderedDict
from functools import wraps
from typing import Any, Callable, Optional

import redis

# 配置日志
logger = logging.getLogger(__name__)

_MISSING = object()


def _env_flag(name: str, default: bool = True) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() not in ("0", "false", "no", "off", "")


def _cache_enabled() -> bool:
    return _env_flag("CACHE_ENABLED", True)


def _redis_url() -> str:
    return os.getenv("REDIS_URL", "").strip()

def _allow_pickle() -> bool:
    # 默认禁用 pickle 反序列化，避免缓存污染导致的反序列化风险
    return _env_flag("CACHE_ALLOW_PICKLE", False)


def _json_dumps_stable(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")


def _json_loads_bytes(raw: bytes) -> Any:
    return json.loads(raw.decode("utf-8"))


def _normalize_for_key(value: Any) -> Any:
    # 只用于生成 key：需要稳定、可序列化、且不引入敏感信息（尽量使用 str/基础类型）
    try:
        from pydantic import BaseModel as _PydanticBaseModel  # type: ignore
    except Exception:  # pragma: no cover
        _PydanticBaseModel = None

    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, bytes):
        return {"__bytes__": hashlib.sha256(value).hexdigest()}
    if isinstance(value, (list, tuple)):
        return [_normalize_for_key(v) for v in value]
    if isinstance(value, set):
        return sorted(_normalize_for_key(v) for v in value)
    if isinstance(value, dict):
        return {str(k): _normalize_for_key(v) for k, v in sorted(value.items(), key=lambda kv: str(kv[0]))}
    if _PydanticBaseModel is not None and isinstance(value, _PydanticBaseModel):
        return _normalize_for_key(value.model_dump())
    # 兜底：用字符串表示（可能包含敏感信息的对象不应作为缓存入参）
    return str(value)


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
            # 默认仅缓存 JSON 可表达的数据；pickle 需要显式开启
            if isinstance(value, bytes):
                serialized = value
            elif isinstance(value, (str, int, float, bool)) or value is None:
                serialized = _json_dumps_stable(value)
            else:
                # 尝试 JSON；失败时按配置决定是否允许 pickle
                try:
                    serialized = _json_dumps_stable(value)
                except Exception:
                    if not _allow_pickle():
                        logger.warning("跳过缓存（非JSON可序列化且未开启 CACHE_ALLOW_PICKLE）：%s", key)
                        return False
                    import pickle  # 延迟导入
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
            
            # 反序列化：优先 JSON；pickle 只有显式允许时才会尝试
            if isinstance(value, bytes):
                try:
                    return _json_loads_bytes(value)
                except Exception:
                    if _allow_pickle():
                        try:
                            import pickle  # 延迟导入
                            return pickle.loads(value)
                        except Exception:
                            return default
                    return default
            # decode_responses=False 时一般是 bytes；这里做兜底
            try:
                return json.loads(str(value))
            except Exception:
                return default
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


class MemoryCache:
    """轻量内存 TTL 缓存（Redis 不可用时的降级）。"""

    def __init__(self, default_ttl: int = 300, max_items: int = 2048):
        self.default_ttl = default_ttl
        self.max_items = max_items
        self._lock = threading.Lock()
        # key -> (expires_at, value)
        self._store: OrderedDict[str, tuple[float, Any]] = OrderedDict()

    def connect(self) -> bool:
        return True

    def is_connected(self) -> bool:
        return True

    def get_client(self):
        return None

    def _now(self) -> float:
        return time.time()

    def _prune(self) -> None:
        now = self._now()
        # 清理过期
        expired = [k for k, (exp, _v) in self._store.items() if exp <= now]
        for k in expired:
            self._store.pop(k, None)
        # 控制容量（LRU）
        while len(self._store) > self.max_items:
            self._store.popitem(last=False)

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        ttl = ttl if ttl is not None else self.default_ttl
        expires_at = self._now() + max(0, int(ttl))
        with self._lock:
            self._store[key] = (expires_at, value)
            self._store.move_to_end(key)
            self._prune()
        return True

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            item = self._store.get(key)
            if not item:
                return default
            expires_at, value = item
            if expires_at <= self._now():
                self._store.pop(key, None)
                return default
            self._store.move_to_end(key)
            return value

    def delete(self, key: str) -> bool:
        with self._lock:
            return self._store.pop(key, None) is not None

    def exists(self, key: str) -> bool:
        return self.get(key, default=_MISSING) is not _MISSING

    def clear_pattern(self, pattern: str) -> int:
        with self._lock:
            keys = [k for k in self._store.keys() if fnmatch.fnmatch(k, pattern)]
            for k in keys:
                self._store.pop(k, None)
            return len(keys)

    def increment(self, key: str, amount: int = 1) -> Optional[int]:
        with self._lock:
            current = self.get(key, default=0)
            try:
                new_val = int(current) + int(amount)
            except Exception:
                new_val = int(amount)
            self.set(key, new_val, ttl=self.default_ttl)
            return new_val

    def get_stats(self) -> dict:
        with self._lock:
            self._prune()
            return {"connected": True, "backend": "memory", "items": len(self._store), "max_items": self.max_items}


class CacheManager:
    """Redis 优先，失败降级到内存缓存。"""

    def __init__(self, redis_cache: RedisCache, memory_cache: Optional[MemoryCache]):
        self._redis = redis_cache
        self._memory = memory_cache

    def is_connected(self) -> bool:
        return self._redis.is_connected() or (self._memory is not None and self._memory.is_connected())

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        if self._redis.is_connected() and self._redis.set(key, value, ttl):
            return True
        if self._memory is not None:
            return self._memory.set(key, value, ttl)
        return False

    def get(self, key: str, default: Any = None) -> Any:
        if self._redis.is_connected():
            val = self._redis.get(key, default=_MISSING)
            if val is not _MISSING:
                return val
        if self._memory is not None:
            return self._memory.get(key, default=default)
        return default

    def delete(self, key: str) -> bool:
        ok = False
        if self._redis.is_connected():
            ok = self._redis.delete(key) or ok
        if self._memory is not None:
            ok = self._memory.delete(key) or ok
        return ok

    def exists(self, key: str) -> bool:
        if self._redis.is_connected() and self._redis.exists(key):
            return True
        if self._memory is not None and self._memory.exists(key):
            return True
        return False

    def clear_pattern(self, pattern: str) -> int:
        deleted = 0
        if self._redis.is_connected():
            deleted += self._redis.clear_pattern(pattern)
        if self._memory is not None:
            deleted += self._memory.clear_pattern(pattern)
        return deleted

    def increment(self, key: str, amount: int = 1) -> Optional[int]:
        if self._redis.is_connected():
            val = self._redis.increment(key, amount)
            if val is not None:
                return int(val)
        if self._memory is not None:
            return self._memory.increment(key, amount)
        return None

    def get_stats(self) -> dict:
        stats = {"connected": self.is_connected(), "backend": "hybrid"}
        stats["redis"] = self._redis.get_stats()
        stats["memory"] = self._memory.get_stats() if self._memory is not None else {"connected": False}
        return stats


def cache_key_generator(*args, **kwargs) -> str:
    """
    生成缓存键
    
    Args:
        *args: 位置参数
        **kwargs: 关键字参数
        
    Returns:
        缓存键字符串
    """
    normalized = {
        "args": _normalize_for_key(list(args)),
        "kwargs": _normalize_for_key(kwargs),
    }
    key_data = _json_dumps_stable(normalized)
    return hashlib.sha256(key_data).hexdigest()


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
_cache_instance: Optional[CacheManager] = None


def init_cache(host: str = 'localhost', port: int = 6379, 
               db: int = 0, password: Optional[str] = None,
               default_ttl: int = 300) -> CacheManager:
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

        redis_cache = RedisCache(
            host=host, port=port, db=db, 
            password=password, default_ttl=default_ttl
        )
        redis_cache.connect()

        mem_enabled = _env_flag("MEMORY_CACHE_ENABLED", True)
        mem_max = int(os.getenv("MEMORY_CACHE_MAX_ITEMS", "2048"))
        memory_cache = MemoryCache(default_ttl=default_ttl, max_items=mem_max) if mem_enabled else None

        _cache_instance = CacheManager(redis_cache=redis_cache, memory_cache=memory_cache)
    return _cache_instance


def get_cache() -> Optional[CacheManager]:
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