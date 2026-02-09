#!/usr/bin/env python3
"""
最小化测试 - 直接测试SQLite数据库
"""

import sqlite3
import json
import os

def test_database():
    """测试数据库连接和基本查询"""
    print("="*80)
    print("SQLite数据库测试")
    print("="*80)
    
    db_path = "gas_data.db"
    if not os.path.exists(db_path):
        print(f"✗ 数据库文件不存在: {db_path}")
        return False
    
    try:
        # 连接数据库
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # 返回字典格式
        cursor = conn.cursor()
        
        print("1. 检查表结构...")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"   表数量: {len(tables)}")
        for table in tables:
            print(f"   - {table['name']}")
        
        print("\n2. 检查gas_mixture表...")
        cursor.execute("PRAGMA table_info(gas_mixture)")
        columns = cursor.fetchall()
        print(f"   列数量: {len(columns)}")
        for col in columns[:5]:  # 只显示前5列
            print(f"   - {col[1]}: {col[2]}")
        if len(columns) > 5:
            print(f"   ... 还有 {len(columns)-5} 列")
        
        print("\n3. 统计记录...")
        cursor.execute("SELECT COUNT(*) as count FROM gas_mixture")
        count = cursor.fetchone()[0]
        print(f"   总记录数: {count:,}")
        
        cursor.execute("SELECT MIN(temperature) as min_temp, MAX(temperature) as max_temp FROM gas_mixture")
        temp_range = cursor.fetchone()
        print(f"   温度范围: {temp_range['min_temp']:.1f} - {temp_range['max_temp']:.1f} K")
        
        cursor.execute("SELECT MIN(pressure) as min_pressure, MAX(pressure) as max_pressure FROM gas_mixture")
        pressure_range = cursor.fetchone()
        print(f"   压力范围: {pressure_range['min_pressure']:.2f} - {pressure_range['max_pressure']:.2f} MPa")
        
        print("\n4. 测试查询性能...")
        import time
        start = time.time()
        cursor.execute("SELECT * FROM gas_mixture WHERE temperature BETWEEN 200 AND 300 LIMIT 10")
        sample_records = cursor.fetchall()
        query_time = (time.time() - start) * 1000
        print(f"   查询时间: {query_time:.2f} ms")
        print(f"   样本记录: {len(sample_records)} 条")
        
        if sample_records:
            print(f"   第一条样本:")
            record = dict(sample_records[0])
            for key in list(record.keys())[:5]:  # 只显示前5个字段
                print(f"     {key}: {record[key]}")
        
        print("\n5. 检查索引...")
        cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='index' AND tbl_name='gas_mixture'")
        indexes = cursor.fetchall()
        print(f"   索引数量: {len(indexes)}")
        for idx in indexes[:3]:
            print(f"   - {idx['name']}")
        if len(indexes) > 3:
            print(f"   ... 还有 {len(indexes)-3} 个索引")
        
        conn.close()
        
        print("\n" + "="*80)
        print("数据库测试完成 - 所有检查通过")
        print("="*80)
        
        return True
        
    except Exception as e:
        print(f"\n✗ 数据库测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_chart_data():
    """测试图表数据生成"""
    print("\n" + "="*80)
    print("图表数据生成测试")
    print("="*80)
    
    db_path = "gas_data.db"
    if not os.path.exists(db_path):
        print(f"✗ 数据库文件不存在: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        print("1. 温度分布数据...")
        cursor.execute('''
            SELECT 
                CAST((temperature / 20) AS INTEGER) * 20 as temp_range,
                COUNT(*) as count
            FROM gas_mixture
            GROUP BY temp_range
            ORDER BY temp_range
        ''')
        temp_data = cursor.fetchall()
        print(f"   温度区间数量: {len(temp_data)}")
        for row in temp_data[:3]:
            print(f"   - {row['temp_range']}K: {row['count']}条记录")
        if len(temp_data) > 3:
            print(f"   ... 还有 {len(temp_data)-3} 个区间")
        
        print("\n2. 压力分布数据...")
        cursor.execute('''
            SELECT 
                CASE 
                    WHEN pressure < 1 THEN '0-1'
                    WHEN pressure < 5 THEN '1-5'
                    WHEN pressure < 10 THEN '5-10'
                    WHEN pressure < 50 THEN '10-50'
                    WHEN pressure < 100 THEN '50-100'
                    ELSE '100+'
                END as pressure_range,
                COUNT(*) as count
            FROM gas_mixture
            GROUP BY pressure_range
            ORDER BY 
                CASE pressure_range
                    WHEN '0-1' THEN 1
                    WHEN '1-5' THEN 2
                    WHEN '5-10' THEN 3
                    WHEN '10-50' THEN 4
                    WHEN '50-100' THEN 5
                    ELSE 6
                END
        ''')
        pressure_data = cursor.fetchall()
        print(f"   压力区间数量: {len(pressure_data)}")
        for row in pressure_data:
            print(f"   - {row['pressure_range']} MPa: {row['count']}条记录")
        
        print("\n3. 散点图数据...")
        cursor.execute('''
            SELECT temperature, pressure
            FROM gas_mixture
            ORDER BY RANDOM()
            LIMIT 50
        ''')
        scatter_data = cursor.fetchall()
        print(f"   采样点数量: {len(scatter_data)}")
        if scatter_data:
            print(f"   第一个点: {scatter_data[0]['temperature']:.1f}K, {scatter_data[0]['pressure']:.2f}MPa")
        
        print("\n4. 组分比例数据...")
        cursor.execute('''
            SELECT 
                AVG(x_ch4) as avg_ch4,
                AVG(x_c2h6) as avg_c2h6,
                AVG(x_c3h8) as avg_c3h8,
                AVG(x_co2) as avg_co2,
                AVG(x_n2) as avg_n2,
                AVG(x_h2s) as avg_h2s,
                AVG(x_ic4h10) as avg_ic4h10
            FROM gas_mixture
        ''')
        composition = cursor.fetchone()
        components = ['CH₄', 'C₂H₆', 'C₃H₈', 'CO₂', 'N₂', 'H₂S', 'i-C₄H₁₀']
        values = [
            composition['avg_ch4'] * 100,
            composition['avg_c2h6'] * 100,
            composition['avg_c3h8'] * 100,
            composition['avg_co2'] * 100,
            composition['avg_n2'] * 100,
            composition['avg_h2s'] * 100,
            composition['avg_ic4h10'] * 100
        ]
        print(f"   组分数量: {len(components)}")
        for i, (name, value) in enumerate(zip(components, values)):
            if i < 3:
                print(f"   - {name}: {value:.2f}%")
        if len(components) > 3:
            print(f"   ... 还有 {len(components)-3} 个组分")
        
        conn.close()
        
        print("\n" + "="*80)
        print("图表数据测试完成 - 数据可生成")
        print("="*80)
        
        return True
        
    except Exception as e:
        print(f"\n✗ 图表数据测试失败: {e}")
        return False

def test_frontend_files():
    """测试前端文件"""
    print("\n" + "="*80)
    print("前端文件测试")
    print("="*80)
    
    files_to_check = [
        ("frontend/index.html", "主页面"),
        ("frontend/css/style.css", "样式表"),
        ("frontend/js/charts.js", "图表脚本"),
    ]
    
    all_exist = True
    for file_path, description in files_to_check:
        if os.path.exists(file_path):
            size = os.path.getsize(file_path) / 1024
            print(f"✓ {description}: {file_path} ({size:.1f} KB)")
        else:
            print(f"✗ {description}: {file_path} (文件不存在)")
            all_exist = False
    
    if all_exist:
        print("\n✓ 所有前端文件存在")
        
        # 检查HTML中的关键元素
        with open("frontend/index.html", "r", encoding="utf-8") as f:
            html = f.read()
        
        checks = [
            ("Chart.js CDN", "cdn.jsdelivr.net/npm/chart.js" in html),
            ("charts.js引用", "js/charts.js" in html),
            ("温度图表容器", 'id="temperatureChart"' in html),
            ("压力图表容器", 'id="pressureChart"' in html),
            ("散点图容器", 'id="scatterChart"' in html),
            ("组分图容器", 'id="compositionChart"' in html),
        ]
        
        print("\nHTML元素检查:")
        for name, exists in checks:
            status = "✓" if exists else "✗"
            print(f"  {status} {name}")
        
    print("\n" + "="*80)
    print("前端文件测试完成")
    print("="*80)
    
    return all_exist

def main():
    """主测试函数"""
    print("气体水合物系统 - 最小化测试")
    print("="*80)
    
    db_ok = test_database()
    chart_ok = test_chart_data()
    frontend_ok = test_frontend_files()
    
    print("\n" + "="*80)
    print("测试结果总结")
    print("="*80)
    
    print(f"数据库测试: {'✓ 通过' if db_ok else '✗ 失败'}")
    print(f"图表数据测试: {'✓ 通过' if chart_ok else '✗ 失败'}")
    print(f"前端文件测试: {'✓ 通过' if frontend_ok else '✗ 失败'}")
    
    print("\n" + "="*80)
    print("系统状态评估")
    print("="*80)
    
    if db_ok and chart_ok and frontend_ok:
        print("状态: ✓ 系统核心组件正常")
        print("\n建议下一步:")
        print("1. 启动后端服务:")
        print("   cd /home/cc/桌面/cursor_shujuku/cursor_shujuku")
        print("   python3 -m backend.main")
        print("\n2. 访问前端页面:")
        print("   http://localhost:8000")
        print("\n3. 测试数据可视化:")
        print("   - 页面加载后应显示统计卡片")
        print("   - 应有4个图表展示数据分布")
        print("\n4. 如果没有Redis，缓存将优雅降级")
    else:
        print("状态: ⚠️ 部分组件存在问题")
        print("\n需要修复:")
        if not db_ok:
            print("  - 数据库连接或查询问题")
        if not chart_ok:
            print("  - 图表数据生成问题")
        if not frontend_ok:
            print("  - 前端文件缺失或损坏")
    
    print("\n" + "="*80)
    print("测试完成")
    print("="*80)

if __name__ == "__main__":
    main()