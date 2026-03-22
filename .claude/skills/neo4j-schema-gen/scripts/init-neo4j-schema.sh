#!/usr/bin/env bash
# 执行 Neo4j Schema 初始化

set -euo pipefail

NEO4J_URI="${NEO4J_URI:-bolt://localhost:7687}"
NEO4J_USER="${NEO4J_USER:-neo4j}"
NEO4J_PASSWORD="${NEO4J_PASSWORD:-password}"
SCHEMA_FILE="${1:-neo4j/init/schema.cypher}"

if [ ! -f "$SCHEMA_FILE" ]; then
  echo "错误：Schema 文件不存在: $SCHEMA_FILE"
  exit 1
fi

echo "正在初始化 Neo4j Schema..."
echo "URI: $NEO4J_URI"

cypher-shell -a "$NEO4J_URI" \
  -u "$NEO4J_USER" \
  -p "$NEO4J_PASSWORD" \
  -f "$SCHEMA_FILE"

echo "Schema 初始化完成"

# 验证
echo "验证约束..."
cypher-shell -a "$NEO4J_URI" \
  -u "$NEO4J_USER" \
  -p "$NEO4J_PASSWORD" \
  "SHOW CONSTRAINTS YIELD name RETURN count(name) AS constraintCount"

echo "验证索引..."
cypher-shell -a "$NEO4J_URI" \
  -u "$NEO4J_USER" \
  -p "$NEO4J_PASSWORD" \
  "SHOW INDEXES YIELD name RETURN count(name) AS indexCount"