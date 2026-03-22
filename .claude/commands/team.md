# 全栈代码工厂 Team

## 可用 Agent

| Agent | 职责 | 触发示例 |
|-------|------|---------|
| `competitor-analyst` | 竞品分析、技术栈识别、可复用模式提取 | 分析竞品 Notion |
| `github-researcher` | GitHub 代码搜索、库/组件发现、最佳实践收集 | 搜索 OAuth 认证代码 |
| `test-engineer` | TDD 测试用例设计、测试执行、验证报告 | 写测试用例 |
| `frontend-dev` | 前端开发（React/Vue/Next.js 按需） | 开发前端组件 |
| `backend-dev` | 后端开发 + Neo4j 集成 | 开发后端 API |

## 可用 Skill

| Skill | 用途 |
|-------|------|
| `competitor-analysis` | 竞品分析（功能对比、技术栈识别、SWOT） |
| `github-search` | GitHub 搜索（代码、仓库、Issue、PR） |
| `tdd-workflow` | TDD 流程（Red-Green-Refactor 循环） |
| `neo4j-schema-gen` | Neo4j Schema 生成（节点、关系、约束、索引） |
| `frontend-react-best-practices` | React 最佳实践（性能优化、Bundle 优化、Hooks） |

## 工作流程

```
用户需求
    |
    v
+-----------------------+
|  competitor-analyst   |  <- 竞品分析
+-----------------------+
    |
    v
+-----------------------+
|   github-researcher   |  <- 代码搜索
+-----------------------+
    |
    v
+-----------------------+
|    test-engineer      |  <- TDD Red: 测试先行
+-----------------------+
    |
    +--------+--------+
    |                 |
    v                 v
+----------+      +----------+
|frontend  |      | backend  |
|  -dev    |      |  -dev    |
+----------+      +----------+
    |                 |
    +--------+--------+
             |
             v
+-----------------------+
|    test-engineer      |  <- TDD Verify: 验证
+-----------------------+
    |
    v
交付成品
```

## 使用方式

### 直接调用 Agent

```
/competitor-analyst 分析 Notion 的技术栈
/github-researcher 搜索 React 认证库
/test-engineer 为用户模块写测试
/frontend-dev 实现登录页面
/backend-dev 创建用户 API
```

### 直接调用 Skill

```
/skill competitor-analysis 分析 Linear
/skill github-search 搜索 Node.js Neo4j 驱动
/skill tdd-workflow 开始认证模块的 TDD 流程
```

## 配置要求

### Neo4j 图数据库

```bash
docker run -d \
  --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password123 \
  neo4j:5-community
```

### 环境变量

```bash
export NEO4J_URI=bolt://localhost:7687
export NEO4J_USER=neo4j
export NEO4J_PASSWORD=password123
export GITHUB_TOKEN=ghp_xxx  # 可选
```

### MCP 服务（可选）

```bash
claude mcp add github
claude mcp add brave-search
```