#!/usr/bin/env python3
"""
简化版后端启动脚本
绕过pymysql导入问题，仅使用SQLite
"""

import os
import sys
import sqlite3
from pathlib import Path

# 设置环境变量，强制使用SQLite
os.environ["DATABASE_URL"] = ""
os.environ["SECURITY_DATABASE_URL"] = ""

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 猴子补丁：在导入backend模块之前修复pymysql问题
class MockPymysql:
    """模拟pymysql模块"""
    class cursors:
        class DictCursor:
            pass
    
    @staticmethod
    def connect(**kwargs):
        raise ImportError("pymysql not available, using SQLite")

# 将模拟模块添加到sys.modules
sys.modules['pymysql'] = MockPymysql
sys.modules['pymysql.cursors'] = MockPymysql.cursors

print("="*80)
print("气体水合物相平衡查询系统 - 简化启动")
print("="*80)
print("配置: 强制使用SQLite模式")
print("环境: DATABASE_URL='' (使用SQLite)")
print("-"*80)

try:
    # 现在导入backend模块
    print("导入backend模块...")
    
    # 检查数据库文件
    db_path = project_root / "gas_data.db"
    if not db_path.exists():
        print(f"错误: 数据库文件不存在: {db_path}")
        sys.exit(1)
    
    print(f"数据库文件: {db_path} ({db_path.stat().st_size / 1024:.1f} KB)")
    
    # 测试数据库连接
    print("\n测试数据库连接...")
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) as count FROM gas_mixture")
    result = cursor.fetchone()
    print(f"✓ 数据库连接成功")
    print(f"  记录总数: {result['count']:,}")
    
    cursor.execute("SELECT MIN(temperature), MAX(temperature) FROM gas_mixture")
    min_temp, max_temp = cursor.fetchone()
    print(f"  温度范围: {min_temp:.1f} - {max_temp:.1f} K")
    
    cursor.execute("SELECT MIN(pressure), MAX(pressure) FROM gas_mixture")
    min_pressure, max_pressure = cursor.fetchone()
    print(f"  压力范围: {min_pressure:.2f} - {max_pressure:.2f} MPa")
    
    conn.close()
    
    # 导入缓存模块（不依赖Redis）
    print("\n初始化缓存模块...")
    try:
        from backend.cache import init_cache
        cache = init_cache()
        if cache.is_connected():
            print("✓ Redis缓存已连接")
        else:
            print("⚠️ Redis未连接 - 缓存将优雅降级")
    except Exception as e:
        print(f"⚠️ 缓存模块初始化失败: {e}")
        print("   缓存功能将不可用，但不影响核心功能")
    
    # 导入FastAPI应用
    print("\n创建FastAPI应用...")
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse
    
    # 创建应用
    app = FastAPI(
        title="气体混合物数据管理系统 API",
        description="简化版本 - 使用SQLite",
        version="4.0.1"
    )
    
    # 配置CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 挂载静态文件
    frontend_dir = project_root / "frontend"
    if frontend_dir.exists():
        app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")
        print(f"✓ 静态文件目录: {frontend_dir}")
    
    # 简单的API端点
    @app.get("/")
    async def root():
        return FileResponse(str(frontend_dir / "index.html"))
    
    @app.get("/api/health")
    async def health_check():
        """健康检查端点"""
        return {
            "status": "healthy",
            "service": "gas_hydrate_api",
            "version": "4.0.1",
            "database": "sqlite",
            "record_count": result['count']
        }
    
    @app.get("/api/statistics")
    async def get_statistics():
        """获取统计信息"""
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total_records,
                AVG(temperature) as avg_temperature,
                AVG(pressure) as avg_pressure,
                MIN(temperature) as min_temperature,
                MAX(temperature) as max_temperature,
                MIN(pressure) as min_pressure,
                MAX(pressure) as max_pressure
            FROM gas_mixture
        """)
        
        stats = cursor.fetchone()
        conn.close()
        
        return {
            "total_records": stats['total_records'],
            "avg_temperature": stats['avg_temperature'],
            "avg_pressure": stats['avg_pressure'],
            "min_temperature": stats['min_temperature'],
            "max_temperature": stats['max_temperature'],
            "min_pressure": stats['min_pressure'],
            "max_pressure": stats['max_pressure']
        }
    
    @app.get("/api/charts/{chart_type}")
    async def get_chart_data(chart_type: str):
        """获取图表数据"""
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if chart_type == 'temperature':
            cursor.execute('''
                SELECT 
                    CAST((temperature / 20) AS INTEGER) * 20 as temp_range,
                    COUNT(*) as count
                FROM gas_mixture
                GROUP BY temp_range
                ORDER BY temp_range
            ''')
            rows = cursor.fetchall()
            conn.close()
            return {
                'labels': [f"{int(r['temp_range'])}-{int(r['temp_range'])+20}K" for r in rows],
                'data': [r['count'] for r in rows],
                'title': '温度分布'
            }
            
        elif chart_type == 'pressure':
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
            rows = cursor.fetchall()
            conn.close()
            return {
                'labels': [f"{r['pressure_range']} MPa" for r in rows],
                'data': [r['count'] for r in rows],
                'title': '压力分布'
            }
            
        elif chart_type == 'scatter':
            cursor.execute('''
                SELECT temperature, pressure
                FROM gas_mixture
                ORDER BY RANDOM()
                LIMIT 200
            ''')
            rows = cursor.fetchall()
            conn.close()
            return {
                'data': [{'x': r['temperature'], 'y': r['pressure']} for r in rows],
                'title': '温度-压力分布'
            }
            
        elif chart_type == 'composition':
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
            row = cursor.fetchone()
            conn.close()
            
            labels = ['CH₄', 'C₂H₆', 'C₃H₈', 'CO₂', 'N₂', 'H₂S', 'i-C₄H₁₀']
            data = [
                row['avg_ch4'] * 100,
                row['avg_c2h6'] * 100,
                row['avg_c3h8'] * 100,
                row['avg_co2'] * 100,
                row['avg_n2'] * 100,
                row['avg_h2s'] * 100,
                row['avg_ic4h10'] * 100
            ]
            
            return {
                "labels": labels,
                "data": data,
                "title": "平均组分比例"
            }
        
        conn.close()
        return {"error": "未知的图表类型"}
    
    # 启动服务器
    print("\n" + "="*80)
    print("启动服务器...")
    print("="*80)
    print("访问地址:")
    print("  前端页面: http://localhost:8000")
    print("  健康检查: http://localhost:8000/api/health")
    print("  统计信息: http://localhost:8000/api/statistics")
    print("  图表数据: http://localhost:8000/api/charts/temperature")
    print("\n按 Ctrl+C 停止服务器")
    print("="*80)
    
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
    
except ImportError as e:
    print(f"\n✗ 导入错误: {e}")
    print("\n缺少依赖包，请尝试安装:")
    print("  pip install fastapi uvicorn")
    print("\n或使用系统包管理器:")
    print("  sudo apt install python3-fastapi python3-uvicorn")
    sys.exit(1)
    
except Exception as e:
    print(f"\n✗ 启动失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)