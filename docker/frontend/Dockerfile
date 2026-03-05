# ==========================================
# 实验室管理系统 - 前端静态文件服务
# ==========================================
FROM nginx:alpine

# 复制前端静态文件
COPY frontend/ /usr/share/nginx/html/

# 复制 nginx 配置（仅静态服务，生产环境由主 nginx 反向代理）
COPY docker/frontend/nginx-static.conf /etc/nginx/conf.d/default.conf

# 暴露端口
EXPOSE 80

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -q -O- http://localhost:80/ || exit 1
