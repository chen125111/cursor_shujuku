from __future__ import annotations

import importlib


def test_memory_cache_fallback(monkeypatch) -> None:
    monkeypatch.setenv("CACHE_ENABLED", "1")
    monkeypatch.setenv("MEMORY_CACHE_ENABLED", "1")
    monkeypatch.delenv("REDIS_URL", raising=False)

    from backend import cache as cache_module

    cache_module = importlib.reload(cache_module)
    cache_module._cache_instance = None

    cache = cache_module.init_cache()
    assert cache.is_connected() is False
    assert cache.is_available() is True

    assert cache.set("unit:test:key", {"ok": True}, ttl=5) is True
    assert cache.get("unit:test:key") == {"ok": True}
    assert cache.exists("unit:test:key") is True

    calls = {"count": 0}

    @cache_module.cached(ttl=30, key_prefix="unit-test")
    def add(x: int, y: int) -> int:
        calls["count"] += 1
        return x + y

    assert add(1, 2) == 3
    assert add(1, 2) == 3
    assert calls["count"] == 1

    assert cache.clear_pattern("cache:*") >= 1
    cache_module._cache_instance = None
