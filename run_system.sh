#!/bin/bash

# 气体水合物相平衡查询系统 - 完整启动脚本

set -e

echo "=========================================="
echo "气体水合物相平衡查询系统"
echo "=========================================="
echo ""

# 检查Python环境
echo "检查Python环境..."
python3 --version || {
    echo "错误: Python3未安装"
    exit 1
}

# 检查依赖
echo "检查依赖..."
if ! python3 -c "import fastapi" 2>/dev/null; then
    echo "安装fastapi..."
    python3 -m pip install --break-system-packages fastapi uvicorn
fi

# 检查数据库文件
echo "检查数据库文件..."
if [ ! -f "gas_data.db" ]; then
    echo "错误: 数据库文件 gas_data.db 不存在"
    exit 1
fi

if [ ! -f "frontend/index.html" ]; then
    echo "错误: 前端文件不存在"
    exit 1
fi

echo "数据库状态:"
python3 << 'EOF'
import sqlite3
import os

db_path = "gas_data.db"
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM gas_mixture")
    count = cursor.fetchone()[0]
    cursor.execute("SELECT MIN(temperature), MAX(temperature) FROM gas_mixture")
    min_temp, max_temp = cursor.fetchone()
    cursor.execute("SELECT MIN(pressure), MAX(pressure) FROM gas_mixture")
    min_pressure, max_pressure = cursor.fetchone()
    conn.close()
    
    print(f"  记录数: {count:,}")
    print(f"  温度范围: {min_temp:.1f} - {max_temp:.1f} K")
    print(f"  压力范围: {min_pressure:.2f} - {max_pressure:.2f} MPa")
else:
    print("  数据库文件不存在")
EOF

echo ""
echo "检查Redis缓存..."
if command -v redis-cli >/dev/null 2>&1 && redis-cli ping >/dev/null 2>&1; then
    echo "  ✓ Redis已安装并运行"
    REDIS_AVAILABLE=1
else
    echo "  ⚠️ Redis未运行 - 缓存将优雅降级"
    REDIS_AVAILABLE=0
fi

echo ""
echo "启动服务器..."
echo "=========================================="
echo "访问地址:"
echo "  前端页面: http://localhost:8000"
echo "  API文档: http://localhost:8000/docs"
echo "  健康检查: http://localhost:8000/api/health"
echo ""
echo "可用API端点:"
echo "  GET /api/health              - 健康检查"
echo "  GET /api/statistics          - 统计信息"
echo "  GET /api/charts/temperature  - 温度图表数据"
echo "  GET /api/charts/pressure     - 压力图表数据"
echo "  GET /api/charts/scatter      - 散点图数据"
echo "  GET /api/charts/composition  - 组分比例数据"
echo ""
echo "按 Ctrl+C 停止服务器"
echo "=========================================="

# 设置环境变量
export DATABASE_URL=""
export SECURITY_DATABASE_URL=""

# 启动服务器
exec python3 start_server.py