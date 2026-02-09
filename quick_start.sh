#!/bin/bash
# 气体水合物相平衡查询系统 - 快速启动脚本

echo "=========================================="
echo "气体水合物相平衡查询系统 - Cursor多模型协作"
echo "=========================================="

# 检查Python环境
echo "检查Python环境..."
if command -v python3 &> /dev/null; then
    python_version=$(python3 --version)
    echo "✓ Python3: $python_version"
else
    echo "✗ Python3未安装，请先安装Python3"
    exit 1
fi

# 检查依赖
echo "检查Python依赖..."
if [ -f "requirements.txt" ]; then
    echo "✓ requirements.txt存在"
    echo "安装依赖: pip install -r requirements.txt"
else
    echo "✗ requirements.txt不存在"
    exit 1
fi

# 创建虚拟环境（可选）
read -p "是否创建Python虚拟环境？(y/n): " create_venv
if [[ $create_venv == "y" || $create_venv == "Y" ]]; then
    echo "创建虚拟环境..."
    python3 -m venv venv
    source venv/bin/activate
    echo "虚拟环境已激活"
fi

# 安装依赖
echo "安装Python依赖..."
pip install -r requirements.txt

# 初始化数据库
echo "初始化数据库..."
python3 -c "
from backend.database import init_database
init_database()
print('数据库初始化完成')
"

# 启动分析
echo "运行项目分析..."
python3 start_cursor_collaboration.py

echo ""
echo "=========================================="
echo "下一步："
echo "1. 打开Cursor编辑器"
echo "2. 加载本项目文件夹"
echo "3. 按照README_CURSOR.md中的指南使用不同模型"
echo "4. 开始协作开发"
echo "=========================================="

# 提供Cursor命令示例
echo ""
echo "Cursor命令示例："
echo "  /model gpt-5.2-codex    # 切换到GPT-5.2 Codex模型（后端优化）"
echo "  /model opus-4.6         # 切换到Opus 4.6模型（前端优化）"
echo "  /model fast             # 切换到Fast模型（部署配置）"
echo "  /model kimi             # 切换到Kimi模型（文档编写）"
echo ""
echo "具体任务分配请查看CURSOR_TASK.md文件"