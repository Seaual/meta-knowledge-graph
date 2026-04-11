# CI/CD 代码质量门禁 — 设计文档

**日期**: 2026-04-11
**状态**: 已批准

## 目标

建立 GitHub Actions CI/CD 流水线，为 PR 和 push 到 main 提供自动化代码质量门禁，确保后续功能开发（Neo4j、协作等）在安全网中进行。

## 架构

单文件 `github/workflows/ci.yml`，包含 3 个并行 job，PR 和 push 到 `main` 时触发：

```
push / PR → ci.yml
              ├── lint (ruff + eslint + prettier)
              ├── type-check (pyright + tsc)
              └── test (pytest + vitest)
```

全部通过才算 PR 可合并。初始阶段设置为 allow_failures，1-2 周后改为 required。

## Job 1: Lint

| 步骤 | 工具 | 作用 |
|------|------|------|
| 后端 lint | `ruff check` + `ruff format --check` | Python 代码风格、静态检查 |
| 前端 lint | `eslint .` | TypeScript/React 代码质量 |
| 前端 format | `prettier --check "src/**/*.{ts,tsx}"` | 前端代码格式 |

## Job 2: Type Check

| 步骤 | 工具 | 作用 |
|------|------|------|
| 后端类型 | `pyright` (strict mode) | Python 类型注解检查 |
| 前端类型 | `tsc --noEmit` | TypeScript 类型检查 |

## Job 3: Test

| 步骤 | 工具 | 作用 |
|------|------|------|
| 后端测试 | `pytest tests/` | API 路由、服务层、数据层单元测试 |
| 前端测试 | `vitest run` (jsdom) | 核心组件单元测试 |

## 测试基础设施

### 后端 (pytest)

- `tests/conftest.py`: `test_db` fixture (in-memory SQLite), `test_client` fixture (FastAPI TestClient)
- 测试覆盖：API 路由（概念 CRUD、论文上传）、服务层（PDF 解析）、数据层（repository 操作）

### 前端 (Vitest)

- `vitest.config.ts`: 配置 vitest，jsdom 环境
- `vitest.setup.ts`: Testing Library 配置
- 初始测试：概念卡片、图谱节点搜索、论文上传组件（3-5 个示例）

## 阻塞策略

1. **阶段一**（当前）：CI 运行但不阻塞合并（`allow_failures` 效果）
2. **阶段二**（1-2 周后）：GitHub 分支保护规则设为 required

## 工作量估算

约 1-2 天

## 文件变更

新增/修改的文件：
- `.github/workflows/ci.yml` — CI 流程定义
- `tests/conftest.py` — pytest fixtures
- `tests/test_api_*.py` — API 测试
- `frontend/vitest.config.ts` — Vitest 配置
- `frontend/vitest.setup.ts` — 测试环境配置
- `frontend/src/**/*.test.tsx` — 组件测试
