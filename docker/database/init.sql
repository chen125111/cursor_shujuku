-- 实验室管理系统 MySQL 初始化脚本
-- 注意：应用使用 SQLite 或 MySQL，此脚本用于 MySQL 模式下的可选初始化

-- 创建数据库（如果使用独立 MySQL 容器）
CREATE DATABASE IF NOT EXISTS gas_data CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS security_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 授予权限（根据实际用户配置）
-- GRANT ALL PRIVILEGES ON gas_data.* TO 'gasapp'@'%';
-- GRANT ALL PRIVILEGES ON security_db.* TO 'gasapp'@'%';
-- FLUSH PRIVILEGES;
