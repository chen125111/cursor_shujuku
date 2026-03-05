#!/bin/bash
# ==========================================
# 实验室管理系统 - 备份脚本
# ==========================================
set -e

BACKUP_DIR="${BACKUP_DIR:-./backups}"
DATA_DIR="${DATA_DIR:-./data}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS="${RETENTION_DAYS:-30}"

mkdir -p "$BACKUP_DIR"

echo "[$(date)] 开始备份..."

# 1. 备份数据目录（SQLite 文件等）
if [ -d "$DATA_DIR" ]; then
    ARCHIVE="$BACKUP_DIR/data_$TIMESTAMP.tar.gz"
    tar -czf "$ARCHIVE" -C "$(dirname $DATA_DIR)" "$(basename $DATA_DIR)"
    echo "  数据目录已备份: $ARCHIVE"
fi

# 2. 如使用 Docker，可备份容器内数据
if command -v docker >/dev/null 2>&1; then
    if docker ps --format '{{.Names}}' | grep -q lab-backend; then
        BACKUP_FILE="$BACKUP_DIR/db_$TIMESTAMP.tar.gz"
        docker exec lab-backend tar -czf - -C /app data 2>/dev/null > "$BACKUP_FILE" || true
        if [ -f "$BACKUP_FILE" ] && [ -s "$BACKUP_FILE" ]; then
            echo "  容器数据已备份: $BACKUP_FILE"
        else
            rm -f "$BACKUP_FILE"
        fi
    fi
fi

# 3. 清理过期备份
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +$RETENTION_DAYS -delete 2>/dev/null || true
echo "  已清理 $RETENTION_DAYS 天前的备份"

echo "[$(date)] 备份完成"
