#!/bin/bash
# ==========================================
# 实验室管理系统 - 恢复脚本
# ==========================================
set -e

BACKUP_FILE="${1:?用法: $0 <备份文件路径>}"
DATA_DIR="${DATA_DIR:-./data}"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "错误: 备份文件不存在: $BACKUP_FILE"
    exit 1
fi

echo "警告: 此操作将覆盖当前数据！"
read -p "确认恢复? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "已取消"
    exit 0
fi

# 停止服务（如使用 Docker）
if command -v docker >/dev/null 2>&1; then
    docker compose stop backend 2>/dev/null || true
fi

# 备份当前数据
if [ -d "$DATA_DIR" ]; then
    mv "$DATA_DIR" "${DATA_DIR}.bak.$(date +%Y%m%d_%H%M%S)"
fi

# 恢复
mkdir -p "$(dirname $DATA_DIR)"
tar -xzf "$BACKUP_FILE" -C "$(dirname $DATA_DIR)"
echo "恢复完成: $BACKUP_FILE"

# 启动服务
if command -v docker >/dev/null 2>&1; then
    docker compose up -d backend
fi

echo "请验证数据后删除旧备份: ${DATA_DIR}.bak.*"
