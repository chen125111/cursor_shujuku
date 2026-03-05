#!/bin/bash
# ==========================================
# 生成自签名 SSL 证书（开发/测试用）
# 生产环境请使用 Let's Encrypt
# ==========================================
set -e

DOMAIN="${1:-localhost}"
OUTPUT_DIR="${2:-./certbot/conf/live/$DOMAIN}"

mkdir -p "$OUTPUT_DIR"

openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout "$OUTPUT_DIR/privkey.pem" \
    -out "$OUTPUT_DIR/fullchain.pem" \
    -subj "/CN=$DOMAIN/O=Lab Management/C=CN"

echo "自签名证书已生成: $OUTPUT_DIR"
echo "注意: 浏览器会显示不安全警告，仅用于开发测试"
