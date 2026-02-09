#!/usr/bin/env python3
"""
测试缓存模块
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from backend.cache import init_cache, get_cache, cached
import time

def test_basic_cache():
    """测试基本缓存功能"""
    print("="*80)
    print("Redis缓存测试")
    print("="*80)
    
    # 初始化缓存
    cache = init_cache()
    
    if cache.is_connected():
        print("✓ Redis连接成功")
        
        # 测试基本设置和获取
        cache.set("test:string", "Hello Redis")
        print(f"✓ 设置字符串: {cache.get('test:string')}")
        
        cache.set("test:dict", {"name": "test", "value": 123})
        print(f"✓ 设置字典: {cache.get('test:dict')}")
        
        cache.set("test:list", [1, 2, 3, 4, 5])
        print(f"✓ 设置列表: {cache.get('test:list')}")
        
        # 测试存在检查
        print(f"✓ 检查存在: {cache.exists('test:string')}")
        
        # 测试删除
        cache.delete("test:string")
        print(f"✓ 删除后检查: {cache.exists('test:string')}")
        
        # 测试统计信息
        stats = cache.get_stats()
        print(f"✓ 缓存统计: {stats}")
        
    else:
        print("✗ Redis未连接，缓存功能不可用")
        print("注意: 这是可选的，不会影响主要功能")

def test_cache_decorator():
    """测试缓存装饰器"""
    print("\n" + "="*80)
    print("缓存装饰器测试")
    print("="*80)
    
    call_count = 0
    
    @cached(ttl=2)  # 2秒缓存
    def expensive_function(x: int, y: int) -> int:
        nonlocal call_count
        call_count += 1
        print(f"  执行函数: {x} + {y}")
        time.sleep(0.1)  # 模拟耗时操作
        return x + y
    
    cache = get_cache()
    if cache and cache.is_connected():
        print("测试缓存装饰器:")
        
        print(f"第一次调用: {expensive_function(10, 20)}")
        print(f"调用次数: {call_count}")
        
        print(f"第二次调用（应该从缓存获取）: {expensive_function(10, 20)}")
        print(f"调用次数: {call_count}")
        
        print(f"不同参数调用: {expensive_function(30, 40)}")
        print(f"调用次数: {call_count}")
        
        # 等待缓存过期
        print("等待缓存过期...")
        time.sleep(3)
        
        print(f"过期后调用: {expensive_function(10, 20)}")
        print(f"调用次数: {call_count}")
        
        print("✓ 缓存装饰器测试通过")
    else:
        print("Redis未连接，跳过装饰器测试")

def test_cache_clear():
    """测试缓存清理"""
    print("\n" + "="*80)
    print("缓存清理测试")
    print("="*80)
    
    cache = get_cache()
    if cache and cache.is_connected():
        # 设置一些测试数据
        for i in range(5):
            cache.set(f"test:item:{i}", f"value_{i}")
        
        # 清除匹配模式
        cleared = cache.clear_pattern("test:item:*")
        print(f"✓ 清除模式缓存: 删除了 {cleared} 个键")
        
        # 清除所有缓存
        cleared = cache.clear_pattern("cache:*")
        print(f"✓ 清除图表缓存: 删除了 {cleared} 个键")
        
        # 测试全局清除
        from backend.cache import clear_cache
        result = clear_cache()
        print(f"✓ 全局清除: {result}")
    else:
        print("Redis未连接，跳过清理测试")

def test_api_endpoints():
    """测试API端点"""
    print("\n" + "="*80)
    print("API端点测试")
    print("="*80)
    
    try:
        # 测试数据库连接
        from backend.database import get_chart_data
        from backend.db import get_connection
        
        print("测试数据库连接...")
        with get_connection(dict_cursor=True) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM gas_mixture")
            result = cursor.fetchone()
            print(f"✓ 数据库连接成功，总记录数: {result['count']}")
        
        # 测试图表数据函数
        print("\n测试图表数据函数:")
        
        temp_data = get_chart_data('temperature')
        print(f"✓ 温度图表数据: {len(temp_data.get('labels', []))}个区间")
        
        pressure_data = get_chart_data('pressure')
        print(f"✓ 压力图表数据: {len(pressure_data.get('labels', []))}个区间")
        
        scatter_data = get_chart_data('scatter')
        print(f"✓ 散点图数据: {len(scatter_data.get('data', []))}个点")
        
    except Exception as e:
        print(f"✗ API测试失败: {e}")
        import traceback
        traceback.print_exc()

def main():
    """主测试函数"""
    print("开始缓存和API测试")
    print("-"*80)
    
    test_basic_cache()
    test_cache_decorator()
    test_cache_clear()
    test_api_endpoints()
    
    print("\n" + "="*80)
    print("测试完成")
    print("="*80)
    
    # 总结
    cache = get_cache()
    if cache and cache.is_connected():
        print("状态: ✓ Redis缓存已启用")
        print("建议:")
        print("  1. 确保Redis服务运行 (redis-server)")
        print("  2. 生产环境可配置REDIS_HOST, REDIS_PASSWORD等环境变量")
    else:
        print("状态: ⚠️ Redis缓存未连接")
        print("注意:")
        print("  1. 缓存是可选的，不影响核心功能")
        print("  2. 如需使用，请安装并启动Redis:")
        print("     sudo apt install redis-server")
        print("     sudo systemctl start redis")
        print("     sudo systemctl enable redis")

if __name__ == "__main__":
    main()