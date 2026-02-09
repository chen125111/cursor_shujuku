#!/usr/bin/env python3
"""
检查数据库状态和性能
"""

import sqlite3
import time
from pathlib import Path

def check_database_stats():
    """检查数据库统计信息"""
    db_path = Path(__file__).parent / "gas_data.db"
    
    if not db_path.exists():
        print("数据库文件不存在")
        return
    
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("="*80)
    print("数据库状态检查")
    print("="*80)
    
    # 1. 检查记录数量
    cursor.execute("SELECT COUNT(*) as count FROM gas_mixture")
    total_records = cursor.fetchone()[0]
    print(f"1. 总记录数: {total_records:,}")
    
    # 2. 检查表结构
    cursor.execute("PRAGMA table_info(gas_mixture)")
    columns = cursor.fetchall()
    print(f"\n2. 表结构 ({len(columns)}列):")
    for col in columns:
        print(f"   - {col[1]}: {col[2]} {'(NOT NULL)' if col[3] else ''}")
    
    # 3. 检查索引
    cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='index' AND tbl_name='gas_mixture'")
    indexes = cursor.fetchall()
    print(f"\n3. 索引信息 ({len(indexes)}个索引):")
    for idx in indexes:
        print(f"   - {idx[0]}: {idx[1]}")
    
    # 4. 检查数据分布
    print("\n4. 数据分布统计:")
    
    # 温度分布
    cursor.execute("""
        SELECT 
            MIN(temperature) as min_temp,
            MAX(temperature) as max_temp,
            AVG(temperature) as avg_temp,
            COUNT(DISTINCT temperature) as unique_temps
        FROM gas_mixture
    """)
    temp_stats = cursor.fetchone()
    print(f"   温度: {temp_stats[0]:.2f}K - {temp_stats[1]:.2f}K, 平均: {temp_stats[2]:.2f}K, 唯一值: {temp_stats[3]}")
    
    # 压力分布
    cursor.execute("""
        SELECT 
            MIN(pressure) as min_pressure,
            MAX(pressure) as max_pressure,
            AVG(pressure) as avg_pressure,
            COUNT(DISTINCT pressure) as unique_pressures
        FROM gas_mixture
    """)
    pressure_stats = cursor.fetchone()
    print(f"   压力: {pressure_stats[0]:.2f} - {pressure_stats[1]:.2f} MPa, 平均: {pressure_stats[2]:.2f} MPa, 唯一值: {pressure_stats[3]}")
    
    # 5. 性能测试 - 简单查询
    print("\n5. 查询性能测试:")
    
    # 测试1: 按ID查询
    start = time.time()
    cursor.execute("SELECT * FROM gas_mixture WHERE id = 1")
    _ = cursor.fetchone()
    time1 = (time.time() - start) * 1000
    print(f"   按ID查询: {time1:.2f} ms")
    
    # 测试2: 温度范围查询
    start = time.time()
    cursor.execute("SELECT COUNT(*) FROM gas_mixture WHERE temperature BETWEEN 200 AND 300")
    _ = cursor.fetchone()
    time2 = (time.time() - start) * 1000
    print(f"   温度范围查询: {time2:.2f} ms")
    
    # 测试3: 组分查询
    start = time.time()
    cursor.execute("""
        SELECT COUNT(*) 
        FROM gas_mixture 
        WHERE x_ch4 > 0.5 AND x_c2h6 < 0.1
    """)
    _ = cursor.fetchone()
    time3 = (time.time() - start) * 1000
    print(f"   组分查询: {time3:.2f} ms")
    
    # 6. 数据库文件信息
    db_size = db_path.stat().st_size / (1024 * 1024)
    print(f"\n6. 数据库文件大小: {db_size:.2f} MB")
    
    # 7. 建议
    print("\n7. 优化建议:")
    
    if total_records > 10000:
        print("   ⚠️  数据量较大，建议:")
        print("   - 添加复合索引优化查询性能")
        print("   - 考虑分表或分区")
        print("   - 添加查询缓存机制")
    
    if len(indexes) < 5:
        print("   ⚠️  索引数量不足，建议添加:")
        print("   - 温度-压力复合索引")
        print("   - 常用组分组合索引")
        print("   - 时间范围索引")
    
    if time2 > 100 or time3 > 100:
        print("   ⚠️  查询性能较慢，建议:")
        print("   - 优化查询语句")
        print("   - 添加缺失索引")
        print("   - 考虑数据预计算")
    
    conn.close()
    
    print("\n" + "="*80)
    print("检查完成")
    print("="*80)

if __name__ == "__main__":
    check_database_stats()