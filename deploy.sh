#!/bin/bash
# Meta Knowledge Graph 一键部署脚本 (Linux/Mac)

set -e

echo "=========================================="
echo "  Meta Knowledge Graph 一键部署"
echo "=========================================="

# 检查 Docker 是否安装
if ! command -v docker &> /dev/null; then
    echo "错误: Docker 未安装"
    echo "请先安装 Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

# 检查 Docker 是否运行
if ! docker info &> /dev/null; then
    echo "错误: Docker 未运行"
    echo "请启动 Docker Desktop 或 Docker 服务"
    exit 1
fi

# 设置端口
PORT=${1:-8088}

echo ""
echo "部署配置:"
echo "  - 端口: $PORT"
echo "  - 镜像: danceinsophy/meta-knowledge-graph:latest"
echo ""

# 拉取镜像
echo ">>> 拉取 Docker 镜像..."
docker pull danceinsophy/meta-knowledge-graph:latest

# 停止并删除旧容器（如果存在）
if docker ps -a --format '{{.Names}}' | grep -q "^meta-knowledge-graph$"; then
    echo ">>> 停止并删除旧容器..."
    docker stop meta-knowledge-graph 2>/dev/null || true
    docker rm meta-knowledge-graph 2>/dev/null || true
fi

# 创建数据目录
echo ">>> 创建数据目录..."
mkdir -p ./mkg-data

# 启动容器
echo ">>> 启动容器..."
docker run -d \
    --name meta-knowledge-graph \
    -p $PORT:8088 \
    -v $(pwd)/mkg-data:/app/data \
    -v $(pwd)/mkg-papers:/app/papers \
    --restart unless-stopped \
    danceinsophy/meta-knowledge-graph:latest

# 等待服务启动
echo ">>> 等待服务启动..."
sleep 5

# 检查服务状态
if docker ps --format '{{.Names}}' | grep -q "^meta-knowledge-graph$"; then
    echo ""
    echo "=========================================="
    echo "  部署成功!"
    echo "=========================================="
    echo ""
    echo "访问地址: http://localhost:$PORT"
    echo ""
    echo "常用命令:"
    echo "  查看日志:   docker logs meta-knowledge-graph"
    echo "  停止服务:   docker stop meta-knowledge-graph"
    echo "  启动服务:   docker start meta-knowledge-graph"
    echo "  删除服务:   docker rm -f meta-knowledge-graph"
    echo ""
else
    echo "错误: 容器启动失败"
    docker logs meta-knowledge-graph
    exit 1
fi