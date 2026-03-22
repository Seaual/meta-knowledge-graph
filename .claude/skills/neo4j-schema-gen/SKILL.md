---
name: neo4j-schema-gen
description: |
  Activate when designing or generating Neo4j database schema.
  Handles: node labels, relationship types, constraints, indexes, Cypher generation.
  Keywords: neo4j, graph database, schema, cypher, nodes, relationships, constraints.
  Do NOT use for: query writing (use cypher skill), data migration (use migration tools).
allowed-tools: [Read, Write, Bash]
---

# Neo4j Schema Generator Skill

根据业务需求生成 Neo4j Schema（节点、关系、约束、索引）。

## 前置检查

检查 Neo4j 连接配置：

```bash
# 检查环境变量
echo "NEO4J_URI: ${NEO4J_URI:-未设置}"
echo "NEO4J_USER: ${NEO4J_USER:-未设置}"

# 测试连接（如果 cypher-shell 可用）
cypher-shell -a "${NEO4J_URI:-bolt://localhost:7687}" \
  -u "${NEO4J_USER:-neo4j}" \
  -p "${NEO4J_PASSWORD:-password}" \
  "RETURN 1"
```

## 执行步骤

### Step 1：分析业务实体

从需求文档或代码中提取业务实体：

**输入来源**：
- `.claude/workspace/user-requirements.md`
- 现有代码中的类型定义
- API 接口文档

**实体提取模板**：

| 实体名称 | 描述 | 主要属性 | 标识属性 |
|---------|------|---------|---------|
| User | 系统用户 | email, name, createdAt | id |
| Project | 项目 | name, description, status | id |
| Task | 任务 | title, priority, dueDate | id |

### Step 2：设计节点标签和属性

为每个实体设计节点标签：

**命名规则**：
- 标签：PascalCase（如 `User`、`Project`）
- 属性：camelCase（如 `createdAt`、`dueDate`）

**属性类型映射**：

| TypeScript 类型 | Neo4j 类型 |
|----------------|-----------|
| string | String |
| number | Integer / Float |
| boolean | Boolean |
| Date | LocalDateTime |
| string[] | List<String> |

**输出**：

```cypher
// 节点标签定义
// User 节点
// 属性: id (String, 必需), email (String, 必需), name (String, 可选), createdAt (LocalDateTime, 必需)

// Project 节点
// 属性: id (String, 必需), name (String, 必需), description (String, 可选), status (String, 必需)
```

### Step 3：设计关系类型和属性

分析实体之间的关系：

**关系提取模板**：

| 关系名称 | 起始节点 | 终止节点 | 属性 | 基数 |
|---------|---------|---------|------|-----|
| OWNS | User | Project | createdAt | 1:N |
| ASSIGNED_TO | User | Task | role | N:M |
| CONTAINS | Project | Task | order | 1:N |

**命名规则**：
- 关系类型：UPPER_SNAKE_CASE（如 `OWNS`、`ASSIGNED_TO`）

**输出**：

```cypher
// 关系类型定义
// [:OWNS] - User -> Project
// [:ASSIGNED_TO] - User -> Task, 属性: role (String, 可选)
// [:CONTAINS] - Project -> Task, 属性: order (Integer, 可选)
```

### Step 4：生成约束和索引

**约束类型**：

| 约束类型 | 用途 | 示例 |
|---------|------|-----|
| UNIQUE | 唯一性约束 | 用户 ID 唯一 |
| EXISTS | 非空约束 | 邮箱必填 |
| KEY | 复合唯一约束 | (tenantId, email) 唯一 |

**索引类型**：

| 索引类型 | 用途 | 示例 |
|---------|------|-----|
| RANGE | 范围查询 | 按日期范围查询 |
| TEXT | 全文搜索 | 搜索项目名称 |
| POINT | 地理查询 | 按位置查询 |

**生成 Cypher**：

```cypher
// ==================== 约束 ====================

// User 节点约束
CREATE CONSTRAINT user_id_unique IF NOT EXISTS
FOR (u:User) REQUIRE u.id IS UNIQUE;

CREATE CONSTRAINT user_email_unique IF NOT EXISTS
FOR (u:User) REQUIRE u.email IS UNIQUE;

// Project 节点约束
CREATE CONSTRAINT project_id_unique IF NOT EXISTS
FOR (p:Project) REQUIRE p.id IS UNIQUE;

// ==================== 索引 ====================

// User 索引
CREATE INDEX user_created_at_index IF NOT EXISTS
FOR (u:User) ON u.createdAt;

// Project 索引
CREATE INDEX project_status_index IF NOT EXISTS
FOR (p:Project) ON p.status;

// 全文索引
CREATE FULLTEXT INDEX project_search IF NOT EXISTS
FOR (p:Project) ON EACH [p.name, p.description];
```

### Step 5：输出 Schema 文件

将 Schema 保存到指定位置：

**文件结构**：

```
neo4j/
├── init/
│   └── schema.cypher      # Schema 初始化脚本
├── constraints/
│   └── constraints.cypher # 约束定义
└── indexes/
    └── indexes.cypher     # 索引定义
```

**主 Schema 文件**：`neo4j/init/schema.cypher`

```cypher
// Neo4j Schema 初始化脚本
// 生成时间: 2024-01-15
// 数据库版本: Neo4j 5.x

// ==================== 节点约束 ====================
// ... 约束定义 ...

// ==================== 节点索引 ====================
// ... 索引定义 ...

// ==================== 验证 ====================
// 运行后验证 Schema
SHOW CONSTRAINTS;
SHOW INDEXES;
```

### Step 6：生成 TypeScript 类型定义

生成对应的 TypeScript 类型：

```typescript
// shared/types/neo4j-nodes.ts

export interface UserNode {
  id: string;
  email: string;
  name?: string;
  createdAt: Date;
}

export interface ProjectNode {
  id: string;
  name: string;
  description?: string;
  status: 'active' | 'archived' | 'deleted';
  createdAt: Date;
}

// shared/types/neo4j-relations.ts

export interface OwnsRelation {
  createdAt: Date;
}

export interface AssignedToRelation {
  role?: 'owner' | 'member' | 'viewer';
}
```

## 辅助脚本

### init-neo4j-schema.sh

```bash
#!/usr/bin/env bash
# 执行 Neo4j Schema 初始化

set -euo pipefail

NEO4J_URI="${NEO4J_URI:-bolt://localhost:7687}"
NEO4J_USER="${NEO4J_USER:-neo4j}"
NEO4J_PASSWORD="${NEO4J_PASSWORD:-password}"
SCHEMA_FILE="neo4j/init/schema.cypher"

if [ ! -f "$SCHEMA_FILE" ]; then
  echo "错误：Schema 文件不存在: $SCHEMA_FILE"
  exit 1
fi

echo "正在初始化 Neo4j Schema..."

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
```

### check-neo4j-connection.sh

```bash
#!/usr/bin/env bash
# 检查 Neo4j 连接状态

set -euo pipefail

NEO4J_URI="${NEO4J_URI:-bolt://localhost:7687}"
NEO4J_USER="${NEO4J_USER:-neo4j}"
NEO4J_PASSWORD="${NEO4J_PASSWORD:-password}"

echo "检查 Neo4j 连接..."
echo "URI: $NEO4J_URI"

if cypher-shell -a "$NEO4J_URI" -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" "RETURN 1" 2>/dev/null; then
  echo "✅ Neo4j 连接成功"
  exit 0
else
  echo "❌ Neo4j 连接失败"
  echo "请检查："
  echo "  1. Neo4j 服务是否运行"
  echo "  2. 环境变量是否正确设置"
  echo "  3. 网络是否可达"
  exit 1
fi
```

## 输出格式

- Schema 文件：`neo4j/init/schema.cypher`
- TypeScript 类型：`shared/types/neo4j-*.ts`
- 设计文档：`.claude/workspace/neo4j-schema-design.md`

## 完成标准

- [ ] 所有实体已转换为节点标签
- [ ] 关系类型定义完整
- [ ] 唯一约束已创建
- [ ] 查询索引已优化
- [ ] Schema 文件可执行
- [ ] TypeScript 类型已生成

## 错误处理

| 错误 | 原因 | 处理方式 |
|-----|------|---------|
| Neo4j 连接失败 | 服务未启动或配置错误 | 检查服务状态和环境变量 |
| 约束已存在 | Schema 重复执行 | 使用 `IF NOT EXISTS` 语法 |
| 属性类型不兼容 | 类型映射错误 | 检查 TypeScript 类型定义 |

## 使用示例

用户输入：「设计一个项目管理系统的 Neo4j Schema」
Skill 行为：
1. 分析业务实体：User、Project、Task、Comment
2. 设计节点标签和属性
3. 设计关系：OWNS、CONTAINS、ASSIGNED_TO、MENTIONS
4. 生成约束和索引
5. 输出 schema.cypher 文件
6. 生成 TypeScript 类型定义

## 配置要求

**环境变量**：

| 变量 | 必需 | 默认值 |
|-----|:----:|-------|
| `NEO4J_URI` | 是 | `bolt://localhost:7687` |
| `NEO4J_USER` | 是 | `neo4j` |
| `NEO4J_PASSWORD` | 是 | `password` |

**Docker Compose**：

```yaml
# neo4j/docker-compose.yml
version: '3.8'
services:
  neo4j:
    image: neo4j:5-community
    container_name: neo4j-dev
    ports:
      - "7474:7474"
      - "7687:7687"
    environment:
      NEO4J_AUTH: neo4j/${NEO4J_PASSWORD:-password123}
      NEO4J_PLUGINS: '["apoc"]'
    volumes:
      - neo4j_data:/data
```