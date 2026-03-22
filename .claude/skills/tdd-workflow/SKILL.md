---
name: tdd-workflow
description: |
  Activate when implementing features using Test-Driven Development (TDD).
  Handles: writing tests before code, Red-Green-Refactor cycle, coverage validation.
  Keywords: tdd, test-driven, write tests, red-green-refactor, unit test, test first.
  Do NOT use for: writing tests after code (use standard testing), debugging existing tests (use debugger).
allowed-tools: [Read, Write, Edit, Bash]
---

# TDD Workflow Skill

测试驱动开发流程技能，遵循 Red-Green-Refactor 三阶段循环。

## 前置检查

确认测试框架已配置：

```bash
# 检查 Jest
npm list jest 2>/dev/null || npm list vitest 2>/dev/null

# 检查 package.json 中的测试脚本
cat package.json | grep -A2 '"scripts"' | grep test
```

支持的测试框架：
- Jest（默认）
- Vitest

## 执行步骤

### Step 1：识别测试目标

分析需求，确定需要测试的单元：

1. 从需求文档或用户故事提取功能点
2. 将功能点拆分为可测试的单元
3. 确定每个单元的输入/输出边界

**输出**：测试目标清单

```markdown
## 测试目标

| 单元 | 功能描述 | 测试类型 |
|-----|---------|---------|
| `authService.login` | 用户登录验证 | 单元测试 |
| `authService.register` | 用户注册 | 单元测试 |
| `POST /api/auth` | 登录接口 | 集成测试 |
```

### Step 2：判断 TDD 强制性

**必须使用 TDD**：
- 核心业务逻辑
- 算法实现
- 安全相关功能
- 支付/交易模块

**可选 TDD**：
- 简单 CRUD 操作
- 配置文件
- UI 组件（可用快照测试代替）

### Step 3：Red 阶段 — 编写失败测试

编写测试用例，确保测试**失败**：

```typescript
// tests/auth.test.ts
import { authService } from '../src/auth';

describe('AuthService', () => {
  describe('login', () => {
    it('should return token for valid credentials', async () => {
      const result = await authService.login('user@test.com', 'password123');
      expect(result.token).toBeDefined();
    });

    it('should throw error for invalid credentials', async () => {
      await expect(
        authService.login('user@test.com', 'wrongpassword')
      ).rejects.toThrow('Invalid credentials');
    });
  });
});
```

运行测试验证失败：

```bash
npm test -- --testPathPattern=auth.test.ts
# 预期：测试失败（因为 authService 尚未实现）
```

**记录**：将测试文件路径写入 `.claude/workspace/test-specs.md`

### Step 4：Green 阶段 — 实现代码

**此步骤由 developer agent 执行**。

实现最小代码使测试通过：

```typescript
// src/auth.ts
export const authService = {
  async login(email: string, password: string) {
    // 最小实现
    if (password === 'password123') {
      return { token: 'mock-token' };
    }
    throw new Error('Invalid credentials');
  }
};
```

运行测试验证通过：

```bash
npm test -- --testPathPattern=auth.test.ts
# 预期：所有测试通过
```

### Step 5：Refactor 阶段 — 优化代码

在测试保护下重构：

1. 移除硬编码
2. 添加错误处理
3. 优化性能
4. 提取重复代码

每次重构后运行测试，确保仍然通过：

```bash
npm test
```

### Step 6：运行覆盖率检查

执行覆盖率分析：

```bash
# Jest
npm test -- --coverage --coverageThreshold='{"global":{"lines":80}}'

# Vitest
npm test -- --coverage
```

检查覆盖率报告：

```markdown
## 覆盖率报告

| 类型 | 覆盖率 | 阈值 | 状态 |
|-----|:------:|:----:|:----:|
| Lines | 85% | 80% | ✅ |
| Functions | 90% | 80% | ✅ |
| Branches | 75% | 80% | ❌ |
| Statements | 85% | 80% | ✅ |
```

如果覆盖率低于阈值，返回 Step 3 补充测试。

### Step 7：输出测试报告

生成测试报告到 `.claude/workspace/test-report.md`：

```markdown
# 测试报告

## 概述
- 测试文件：X 个
- 测试用例：Y 个
- 通过：Y 个
- 失败：0 个
- 覆盖率：Z%

## 测试用例清单
| 文件 | 用例 | 状态 |
|-----|-----|:----:|
| auth.test.ts | login valid | ✅ |
| auth.test.ts | login invalid | ✅ |

## 建议
- [ ] 增加边界条件测试
- [ ] 添加错误场景覆盖
```

## 辅助脚本

### run-tests.sh

```bash
#!/usr/bin/env bash
# 运行测试并生成覆盖率报告

set -euo pipefail

TEST_FRAMEWORK="jest"
if npm list vitest 2>/dev/null | grep -q vitest; then
  TEST_FRAMEWORK="vitest"
fi

echo "使用测试框架: $TEST_FRAMEWORK"

if [ "$TEST_FRAMEWORK" = "vitest" ]; then
  npm test -- --run --coverage
else
  npm test -- --coverage
fi

echo "测试完成"
```

### check-coverage.sh

```bash
#!/usr/bin/env bash
# 检查覆盖率是否达到阈值

set -euo pipefail

THRESHOLD="${1:-80}"
COVERAGE_FILE="coverage/coverage-summary.json"

if [ ! -f "$COVERAGE_FILE" ]; then
  echo "错误：覆盖率文件不存在，请先运行测试"
  exit 1
fi

# 提取行覆盖率
LINE_COVERAGE=$(cat "$COVERAGE_FILE" | grep -o '"lines":{[^}]*}' | grep -o '[0-9]*\.[0-9]*' | head -1)

echo "行覆盖率: ${LINE_COVERAGE}%"

if (( $(echo "$LINE_COVERAGE >= $THRESHOLD" | bc -l) )); then
  echo "✅ 覆盖率达标（阈值: ${THRESHOLD}%）"
  exit 0
else
  echo "❌ 覆盖率不足（阈值: ${THRESHOLD}%）"
  exit 1
fi
```

## 输出格式

- 测试规格：`.claude/workspace/test-specs.md`
- 测试报告：`.claude/workspace/test-report.md`
- 覆盖率报告：`coverage/` 目录

## 完成标准

- [ ] 所有测试用例通过
- [ ] 代码覆盖率 >= 80%
- [ ] 无明显的代码异味
- [ ] 测试报告已生成

## 错误处理

| 错误 | 原因 | 处理方式 |
|-----|------|---------|
| 测试框架未安装 | 项目未配置测试 | 提示安装 Jest 或 Vitest |
| 测试无法运行 | 语法错误或配置问题 | 检查配置文件，修复语法 |
| 覆盖率不足 | 测试覆盖不完整 | 返回 Step 3 补充测试 |
| Refactor 后测试失败 | 重构引入错误 | 回退或修复代码 |

## 使用示例

用户输入：「为用户认证模块编写 TDD 测试」
Skill 行为：
1. 识别测试目标：login、register、logout
2. 判断 TDD 强制性：认证模块属于核心业务，必须 TDD
3. Red：编写 6 个测试用例，运行确认失败
4. Green：通知 developer agent 实现代码
5. Refactor：审查代码质量
6. 检查覆盖率：确保 >= 80%
7. 输出测试报告

## 配置要求

- Jest 或 Vitest
- package.json 中配置测试脚本

```json
{
  "scripts": {
    "test": "jest",
    "test:coverage": "jest --coverage"
  }
}
```