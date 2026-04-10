#!/bin/bash
set -e

echo "🚀 启动测试平台后端服务..."
echo "数据库类型: ${DB_TYPE:-mysql}"
echo "数据库主机: ${DB_HOST:-localhost}"

# 等待数据库服务启动
echo "⏳ 等待数据库服务启动..."
if [ "${DB_TYPE:-mysql}" = "postgresql" ]; then
    echo "等待 PostgreSQL 启动..."
    while ! nc -z ${DB_HOST:-postgres} ${DB_PORT:-5432}; do
        echo "PostgreSQL 未就绪，等待中..."
        sleep 2
    done
    echo "✅ PostgreSQL 已就绪"
else
    echo "等待 MySQL 启动..."
    while ! nc -z ${DB_HOST:-mysql} ${DB_PORT:-3306}; do
        echo "MySQL 未就绪，等待中..."
        sleep 2
    done
    echo "✅ MySQL 已就绪"
fi

# 尝试初始化数据库（无论是否已初始化）
echo "🏗️ 尝试初始化数据库..."
python init_database.py --full || echo "⚠️  数据库可能已初始化，跳过"

# 启动应用
echo "🚀 启动应用服务..."
exec "$@"
