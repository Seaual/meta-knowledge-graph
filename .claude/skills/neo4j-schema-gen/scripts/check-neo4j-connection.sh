#!/usr/bin/env bash
# 检查 Neo4j 连接状态

set -euo pipefail

NEO4J_URI="${NEO4J_URI:-bolt://localhost:7687}"
NEO4J_USER="${NEO4J_USER:-neo4j}"
NEO4J_PASSWORD="${NEO4J_PASSWORD:-password}"

echo "检查 Neo4j 连接..."
echo "URI: $NEO4J_URI"

if cypher-shell -a "$NEO4J_URI" -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" "RETURN 1" 2>/dev/null; then
  echo "Neo4j 连接成功"
  exit 0
else
  echo "Neo4j 连接失败"
  echo "请检查："
  echo "  1. Neo4j 服务是否运行"
  echo "  2. 环境变量是否正确设置"
  echo "  3. 网络是否可达"
  exit 1
fi