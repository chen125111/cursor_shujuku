#!/bin/bash
# ==========================================
# Let's Encrypt SSL 证书初始化脚本
# 使用 Certbot 获取免费 SSL 证书
# ==========================================
# 前置条件: 域名已解析到本机，80 端口可用
# 如 Nginx 已运行，请先停止: docker compose stop nginx
# ==========================================

set -e

# 配置变量
DOMAIN="${1:-yourdomain.com}"
EMAIL="${2:-admin@yourdomain.com}"
STAGING="${3:-0}"  # 设为 1 使用测试环境（避免限流）

if [ -z "$1" ]; then
    echo "用法: $0 <域名> [邮箱] [staging]"
    echo "示例: $0 lab.example.com admin@example.com"
    echo "示例: $0 lab.example.com admin@example.com 1  # 使用测试环境"
    exit 1
fi

# 创建目录
mkdir -p certbot/conf certbot/www

echo "正在获取 SSL 证书..."
echo "域名: $DOMAIN"
echo "邮箱: $EMAIL"
echo "请确保 80 端口未被占用（如有 Nginx 请先停止）"
echo ""

# 使用 standalone 模式（Certbot 临时占用 80 端口）
docker run --rm \
    -p 80:80 \
    -v "$(pwd)/certbot/conf:/etc/letsencrypt" \
    certbot/certbot certonly \
    --standalone \
    --email "$EMAIL" \
    --agree-tos \
    --no-eff-email \
    ${STAGING:+--staging} \
    -d "$DOMAIN"

# 创建 Nginx 使用的标准路径符号链接
mkdir -p certbot/conf/live
ln -sf "$DOMAIN/fullchain.pem" certbot/conf/live/fullchain.pem 2>/dev/null || true
ln -sf "$DOMAIN/privkey.pem" certbot/conf/live/privkey.pem 2>/dev/null || true

echo "证书已获取！"
echo "证书位置: certbot/conf/live/$DOMAIN/"
echo ""
echo "启用 SSL 模式："
echo "  docker compose -f docker-compose.yml -f docker-compose.ssl.yml up -d"
echo "  cp nginx/nginx.conf nginx/nginx.conf.bak"
echo "  确保 nginx.conf 中的 ssl_certificate 指向 certbot/conf/live/$DOMAIN/fullchain.pem"
echo ""
echo "重新加载 nginx："
echo "  docker compose exec nginx nginx -s reload"
