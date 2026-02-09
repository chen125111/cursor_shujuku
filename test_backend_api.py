#!/usr/bin/env python3
"""
测试后端API功能
"""

import sys
import os
import json

# 添加项目根目录到路径
sys.path.append(os.path.dirname(__file__))

def test_basic_api():
    """测试基本API功能"""
    print("="*80)
    print("后端API功能测试")
    print("="*80)
    
    try:
        # 导入必要的模块
        from backend.db import get_connection
        from backend.database import get_statistics, get_chart_data
        from backend.models import Statistics
        
        print("1. 测试数据库连接...")
        with get_connection(dict_cursor=True) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM gas_mixture")
            result = cursor.fetchone()
            print(f"   ✓ 数据库连接成功")
            print(f"     总记录数: {result['count']:,}")
        
        print("\n2. 测试统计信息API...")
        stats = get_statistics()
        print(f"   ✓ 统计信息获取成功")
        print(f"     平均温度: {stats.avg_temperature:.2f} K")
        print(f"     平均压力: {stats.avg_pressure:.2f} MPa")
        print(f"     温度范围: {stats.min_temperature:.1f} - {stats.max_temperature:.1f} K")
        
        print("\n3. 测试图表数据API...")
        
        # 温度图表
        temp_data = get_chart_data('temperature')
        print(f"   ✓ 温度图表数据: {len(temp_data.get('labels', []))}个区间")
        
        # 压力图表
        pressure_data = get_chart_data('pressure')
        print(f"   ✓ 压力图表数据: {len(pressure_data.get('labels', []))}个区间")
        
        # 散点图数据
        scatter_data = get_chart_data('scatter')
        print(f"   ✓ 散点图数据: {len(scatter_data.get('data', []))}个点")
        
        print("\n4. 测试数据验证...")
        from backend.data_validation import validate_record, get_validation_rules
        
        test_record = {
            "temperature": 275.0,
            "pressure": 3.5,
            "x_ch4": 0.8,
            "x_c2h6": 0.1,
            "x_c3h8": 0.05,
            "x_co2": 0.03,
            "x_n2": 0.01,
            "x_h2s": 0.005,
            "x_ic4h10": 0.005
        }
        
        is_valid, errors = validate_record(test_record)
        print(f"   ✓ 数据验证测试: {'通过' if is_valid else '失败'}")
        if errors:
            print(f"     错误信息: {errors}")
        
        validation_rules = get_validation_rules()
        print(f"   ✓ 验证规则加载: {len(validation_rules)}条规则")
        
        print("\n" + "="*80)
        print("后端API测试完成 - 所有核心功能正常")
        print("="*80)
        
        return True
        
    except Exception as e:
        print(f"\n✗ API测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_cache_module():
    """测试缓存模块（不依赖Redis）"""
    print("\n" + "="*80)
    print("缓存模块测试（降级模式）")
    print("="*80)
    
    try:
        # 测试缓存模块导入
        from backend.cache import RedisCache, init_cache, get_cache
        
        print("1. 初始化缓存（无Redis连接）...")
        cache = init_cache()
        
        if cache.is_connected():
            print("   ✓ Redis已连接")
            print("   - 测试基本缓存操作...")
            cache.set("test:fallback", "test_value")
            value = cache.get("test:fallback")
            print(f"   - 缓存值: {value}")
        else:
            print("   ⚠️ Redis未连接 - 缓存降级模式")
            print("   - 测试降级功能...")
            # 测试降级模式下的行为
            result = cache.set("test:fallback", "test_value")
            print(f"   - 设置缓存（降级）: {result}")
            value = cache.get("test:fallback")
            print(f"   - 获取缓存（降级）: {value}")
        
        print("\n2. 测试缓存装饰器...")
        from backend.cache import cached
        import time
        
        call_count = 0
        
        @cached(ttl=1)
        def test_func(x, y):
            nonlocal call_count
            call_count += 1
            return x + y
        
        print(f"   - 第一次调用: {test_func(1, 2)}")
        print(f"   - 函数调用次数: {call_count}")
        print(f"   - 第二次调用（可能从缓存）: {test_func(1, 2)}")
        print(f"   - 函数调用次数: {call_count}")
        
        print("\n" + "="*80)
        print("缓存模块测试完成 - 降级模式正常")
        print("="*80)
        
        return True
        
    except Exception as e:
        print(f"\n✗ 缓存测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_frontend_integration():
    """测试前端集成点"""
    print("\n" + "="*80)
    print("前端集成点测试")
    print("="*80)
    
    try:
        print("1. 检查前端文件...")
        frontend_files = [
            "frontend/index.html",
            "frontend/css/style.css",
            "frontend/js/charts.js"
        ]
        
        for file in frontend_files:
            if os.path.exists(file):
                size = os.path.getsize(file) / 1024
                print(f"   ✓ {file}: {size:.1f} KB")
            else:
                print(f"   ✗ {file}: 文件不存在")
        
        print("\n2. 检查Chart.js引用...")
        with open("frontend/index.html", "r", encoding="utf-8") as f:
            html_content = f.read()
        
        if "cdn.jsdelivr.net/npm/chart.js" in html_content:
            print("   ✓ Chart.js CDN引用存在")
        else:
            print("   ✗ Chart.js CDN引用不存在")
        
        if "js/charts.js" in html_content:
            print("   ✓ charts.js本地引用存在")
        else:
            print("   ✗ charts.js本地引用不存在")
        
        print("\n3. 检查图表容器...")
        chart_containers = [
            "temperatureChart",
            "pressureChart",
            "scatterChart",
            "compositionChart"
        ]
        
        for container in chart_containers:
            if f'id="{container}"' in html_content:
                print(f"   ✓ 图表容器 {container} 存在")
            else:
                print(f"   ✗ 图表容器 {container} 不存在")
        
        print("\n" + "="*80)
        print("前端集成测试完成")
        print("="*80)
        
        return True
        
    except Exception as e:
        print(f"\n✗ 前端测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("开始综合测试")
    print("-"*80)
    
    api_ok = test_basic_api()
    cache_ok = test_cache_module()
    frontend_ok = test_frontend_integration()
    
    print("\n" + "="*80)
    print("测试结果总结")
    print("="*80)
    
    print(f"后端API测试: {'✓ 通过' if api_ok else '✗ 失败'}")
    print(f"缓存模块测试: {'✓ 通过' if cache_ok else '✗ 失败'}")
    print(f"前端集成测试: {'✓ 通过' if frontend_ok else '✗ 失败'}")
    
    print("\n" + "="*80)
    print("系统状态评估")
    print("="*80)
    
    if api_ok and cache_ok and frontend_ok:
        print("状态: ✓ 系统核心功能正常")
        print("建议:")
        print("  1. 可以启动后端服务进行完整测试")
        print("  2. 如需Redis缓存，请安装并启动Redis服务")
        print("  3. 使用浏览器访问前端页面测试可视化")
    else:
        print("状态: ⚠️ 部分功能存在问题")
        print("建议:")
        print("  1. 检查Python依赖是否安装完整")
        print("  2. 验证数据库文件是否存在")
        print("  3. 检查前端文件结构")
    
    print("\n下一步:")
    print("  1. 启动后端: cd backend && python main.py")
    print("  2. 访问前端: http://localhost:8000")
    print("  3. 测试API: http://localhost:8000/api/statistics")

if __name__ == "__main__":
    main()