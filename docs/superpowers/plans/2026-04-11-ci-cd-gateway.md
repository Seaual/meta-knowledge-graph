# CI/CD 代码质量门禁 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立 GitHub Actions CI 流水线，包含 lint、type-check、test 三个并行 job，为 PR 和 main 分支 push 提供自动化代码质量门禁。

**Architecture:** 单文件 `ci.yml` 定义 3 个并行 job。后端使用 ruff + pyright + pytest，前端使用 eslint + prettier + tsc + vitest。初始阶段 CI 运行但不阻塞合并，1-2 周后改为 required。

**Tech Stack:** GitHub Actions, ruff, pyright, pytest, eslint, prettier, vitest, tsc

---

## 文件映射

| 文件 | 类型 | 职责 |
|------|------|------|
| `.github/workflows/ci.yml` | 新增 | CI 流水线定义 |
| `pyproject.toml` | 新增 | Python 项目配置（ruff, pyright 配置） |
| `requirements.txt` | 修改 | 添加 ruff, pyright, pytest 为 dev 依赖 |
| `backend/conftest.py` | 新增 | 后端 pytest fixtures（复用 tests/ 已有模式） |
| `tests/conftest.py` | 新增 | 根目录 pytest 配置 |
| `tests/test_api_health.py` | 新增 | API 路由基础测试 |
| `tests/test_pdf_parser.py` | 新增 | PDF 解析模块测试 |
| `frontend/vitest.config.ts` | 新增 | Vitest 配置 |
| `frontend/vitest.setup.ts` | 新增 | Vitest 测试环境配置 |
| `frontend/src/components/ui/__tests__/` | 新增 | UI 组件测试 |
| `frontend/package.json` | 修改 | 添加 test/lint/format scripts 和 devDependencies |
| `frontend/.eslintrc.cjs` | 新增 | ESLint 配置 |
| `frontend/.prettierrc` | 新增 | Prettier 配置 |

---

### Task 1: 后端 lint/type-check 配置

**Files:**
- Create: `pyproject.toml`
- Modify: `requirements.txt`

- [ ] **Step 1: 创建 pyproject.toml**

```toml
[tool.ruff]
target-version = "py310"
line-length = 120
src = ["backend", "mkg", "tests"]

[tool.ruff.lint]
select = ["E", "F", "W", "I", "UP", "B"]
ignore = ["E501"]

[tool.ruff.lint.isort]
known-first-party = ["backend", "mkg"]

[tool.pyright]
include = ["backend", "mkg"]
pythonVersion = "3.10"
typeCheckingMode = "standard"
```

- [ ] **Step 2: 添加 dev 依赖到 requirements.txt**

在 `requirements.txt` 末尾追加：

```
# Development
ruff>=0.1.0
pyright>=1.1.350
pytest>=7.4.0
pytest-asyncio>=0.23.0
httpx>=0.26.0
```

- [ ] **Step 3: 验证 lint 和 type-check 能运行**

```bash
pip install ruff pyright
ruff check . --no-fix
pyright backend/ mkg/
```

- [ ] **Step 4: 修复 ruff 发现的问题（如有）**

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml requirements.txt
git commit -m "chore: add ruff and pyright configuration for CI lint pipeline"
```

---

### Task 2: 后端测试基础设施与 API 测试

**Files:**
- Create: `tests/conftest.py`
- Create: `tests/test_api_health.py`
- Create: `tests/test_pdf_parser.py`

- [ ] **Step 1: 创建 tests/conftest.py**

复用 `tests/repositories/` 已有的 in-memory SQLite fixture 模式：

```python
"""
Root-level pytest configuration for MKG backend tests.
"""
import sys
from pathlib import Path

import pytest

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient
from mkg.database import Database


@pytest.fixture
def test_db():
    """Create an in-memory SQLite database for testing."""
    db = Database(":memory:")
    db.connect()
    yield db
    db.close()


@pytest.fixture
def app(test_db):
    """Create FastAPI test app with test database."""
    from backend.main import app

    # Override database dependency
    original_deps = app.dependency_overrides.copy()

    yield app

    app.dependency_overrides = original_deps


@pytest.fixture
def client(app):
    """Create test client."""
    with TestClient(app) as c:
        yield c
```

- [ ] **Step 2: 创建 tests/test_api_health.py**

```python
"""
Basic API health check tests.
"""
from fastapi.testclient import TestClient


def test_health_endpoint(client):
    """Test /health returns ok status."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_api_root(client):
    """Test /api returns version info."""
    response = client.get("/api")
    assert response.status_code == 200
    data = response.json()
    assert "version" in data
```

- [ ] **Step 3: 创建 tests/test_pdf_parser.py**

```python
"""
PDF parser module tests.
"""
from mkg.pdf_parser import PDFParser


def test_pdf_parser_instantiation():
    """Test PDFParser can be instantiated."""
    parser = PDFParser()
    assert parser is not None


def test_parse_nonexistent_pdf():
    """Test parsing a non-existent file returns empty result."""
    parser = PDFParser()
    result = parser.parse("nonexistent.pdf")
    assert result is None or result.get("error") is not None
```

- [ ] **Step 4: 运行测试验证**

```bash
pip install pytest httpx fastapi python-multipart
pytest tests/ -v
```

Expected: 所有测试通过（包括 `tests/repositories/` 下已有的 9 个测试 + 新增的 4 个）

- [ ] **Step 5: Commit**

```bash
git add tests/conftest.py tests/test_api_health.py tests/test_pdf_parser.py
git commit -m "test: add backend test infrastructure and basic API tests"
```

---

### Task 3: 前端 lint/type-check 配置

**Files:**
- Create: `frontend/.eslintrc.cjs`
- Create: `frontend/.prettierrc`
- Modify: `frontend/package.json`

- [ ] **Step 1: 安装 eslint + prettier 及其依赖**

```bash
cd frontend
npm install -D eslint prettier @typescript-eslint/parser @typescript-eslint/eslint-plugin eslint-plugin-react eslint-plugin-react-hooks
```

- [ ] **Step 2: 创建 .eslintrc.cjs**

```javascript
module.exports = {
  root: true,
  parser: "@typescript-eslint/parser",
  parserOptions: {
    ecmaVersion: 2020,
    sourceType: "module",
    ecmaFeatures: { jsx: true },
  },
  plugins: ["@typescript-eslint", "react", "react-hooks"],
  extends: [
    "eslint:recommended",
    "plugin:@typescript-eslint/recommended",
    "plugin:react/recommended",
    "plugin:react-hooks/recommended",
  ],
  settings: {
    react: { version: "detect" },
  },
  rules: {
    "react/react-in-jsx-scope": "off",
    "@typescript-eslint/no-unused-vars": "warn",
    "react/prop-types": "off",
  },
  env: {
    browser: true,
    es2020: true,
  },
};
```

- [ ] **Step 3: 创建 .prettierrc**

```json
{
  "semi": true,
  "trailingComma": "es5",
  "singleQuote": false,
  "printWidth": 80,
  "tabWidth": 2
}
```

- [ ] **Step 4: 添加 scripts 到 package.json**

修改 `frontend/package.json` 的 `scripts` 部分：

```json
{
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview",
    "lint": "eslint src --ext .ts,.tsx",
    "lint:fix": "eslint src --ext .ts,.tsx --fix",
    "format": "prettier --check \"src/**/*.{ts,tsx,css}\"",
    "format:fix": "prettier --write \"src/**/*.{ts,tsx,css}\"",
    "typecheck": "tsc --noEmit"
  }
}
```

- [ ] **Step 5: 验证 lint 和 typecheck 能运行**

```bash
cd frontend
npm run typecheck
npm run lint
npm run format
```

- [ ] **Step 6: 修复 lint 发现的问题（如有）**

- [ ] **Step 7: Commit**

```bash
git add frontend/.eslintrc.cjs frontend/.prettierrc frontend/package.json frontend/package-lock.json
git commit -m "chore: add eslint and prettier configuration for frontend CI"
```

---

### Task 4: 前端测试基础设施（Vitest）

**Files:**
- Create: `frontend/vitest.config.ts`
- Create: `frontend/vitest.setup.ts`

- [ ] **Step 1: 安装 Vitest 及测试库**

```bash
cd frontend
npm install -D vitest @testing-library/react @testing-library/jest-dom jsdom
```

- [ ] **Step 2: 创建 vitest.config.ts**

```typescript
/// <reference types="vitest" />
import { defineConfig } from "vite";

export default defineConfig({
  test: {
    environment: "jsdom",
    setupFiles: ["./vitest.setup.ts"],
    globals: true,
    include: ["src/**/*.test.{ts,tsx}"],
  },
});
```

- [ ] **Step 3: 创建 vitest.setup.ts**

```typescript
import "@testing-library/jest-dom";
```

- [ ] **Step 4: 验证 vitest 能运行**

```bash
cd frontend
npx vitest run
```

Expected: 0 个测试文件通过（还未写测试用例）

- [ ] **Step 5: Commit**

```bash
git add frontend/vitest.config.ts frontend/vitest.setup.ts frontend/package.json frontend/package-lock.json
git commit -m "chore: add vitest and testing-library configuration"
```

---

### Task 5: 前端组件测试（示例测试）

**Files:**
- Create: `frontend/src/components/__tests__/drag-upload.test.tsx`
- Create: `frontend/src/components/ui/__tests__/animations.test.tsx`

- [ ] **Step 1: 创建 `frontend/src/components/ui/__tests__/animations.test.tsx`**

`FadeContent` 是纯 UI 动画组件，无外部 API 依赖，适合做第一个测试：

```typescript
import { render, screen } from "@testing-library/react";
import { FadeContent } from "../animations";

describe("FadeContent", () => {
  it("renders children", () => {
    render(<FadeContent>Test Content</FadeContent>);
    expect(screen.getByText("Test Content")).toBeInTheDocument();
  });

  it("applies custom className", () => {
    render(<FadeContent className="custom-class">Styled</FadeContent>);
    expect(screen.getByText("Styled")).toHaveClass("custom-class");
  });
});
```

- [ ] **Step 2: 创建 `frontend/src/components/__tests__/drag-upload.test.tsx`**

`DragUploadZone` 有 lucide-react 图标依赖，需 mock：

```typescript
import { render, screen } from "@testing-library/react";
import { describe, it, vi } from "vitest";

// Mock lucide-react icons
vi.mock("lucide-react", () => ({
  Upload: () => <span data-testid="upload-icon" />,
  Loader2: () => <span data-testid="loader-icon" />,
}));

// Mock API
vi.mock("../../lib/api", () => ({
  papersApi: { upload: vi.fn() },
}));

// Import after mocking
const DragUploadZone = (await import("../DragUploadZone")).default;

describe("DragUploadZone", () => {
  it("renders without crashing", () => {
    render(
      <DragUploadZone
        onUploadSuccess={() => {}}
        onUploadError={() => {}}
      />
    );
    expect(screen.getByText(/drag.*pdf/ii) || screen.getByTestId("upload-icon")).toBeInTheDocument();
  });
});
```

- [ ] **Step 3: 运行测试验证**

```bash
cd frontend
npx vitest run
```

Expected: 4 个测试通过（2 个 FadeContent + 1 个 DragUploadZone + 后续可能加的）

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/__tests__/ frontend/src/components/ui/__tests__/
git commit -m "test: add frontend component tests for FadeContent and DragUploadZone"
```

---

### Task 6: GitHub Actions CI 流水线

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: 创建 CI workflow 文件**

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  lint:
    name: Lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.10"
          cache: "pip"

      - name: Install backend dependencies
        run: pip install -r requirements.txt

      - name: Ruff check
        run: ruff check .

      - name: Ruff format
        run: ruff format --check

      - name: Set up Node
        uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: "npm"
          cache-dependency-path: frontend/package-lock.json

      - name: Install frontend dependencies
        working-directory: frontend
        run: npm ci

      - name: ESLint
        working-directory: frontend
        run: npm run lint

      - name: Prettier
        working-directory: frontend
        run: npm run format

  type-check:
    name: Type Check
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.10"
          cache: "pip"

      - name: Install backend dependencies
        run: pip install -r requirements.txt

      - name: Pyright
        run: pyright backend/ mkg/

      - name: Set up Node
        uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: "npm"
          cache-dependency-path: frontend/package-lock.json

      - name: Install frontend dependencies
        working-directory: frontend
        run: npm ci

      - name: TypeScript check
        working-directory: frontend
        run: npm run typecheck

  test:
    name: Test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.10"
          cache: "pip"

      - name: Install backend dependencies
        run: pip install -r requirements.txt

      - name: Run backend tests
        run: pytest tests/ -v

      - name: Set up Node
        uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: "npm"
          cache-dependency-path: frontend/package-lock.json

      - name: Install frontend dependencies
        working-directory: frontend
        run: npm ci

      - name: Run frontend tests
        working-directory: frontend
        run: npx vitest run
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: add GitHub Actions CI pipeline with lint, type-check, and test jobs"
```

---

### Task 7: 验证 CI 运行并记录后续步骤

**Files:**
- Modify: `README.md` (更新 Roadmap)

- [ ] **Step 1: Push 到远程并观察 CI**

```bash
git push origin main
```

在 GitHub Actions 页面观察 CI 运行结果，修复首次运行时可能出现的 lint 或 type 错误。

- [ ] **Step 2: 更新 README Roadmap**

将 CI/CD 从 Roadmap 中标记为完成。找到 README.md 中的 Roadmap 部分，在合适的位置添加完成标记。

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: update roadmap - CI/CD gateway complete"
```

---

## 依赖关系

```
Task 1 (后端 lint 配置)
        ↓
Task 2 (后端测试)  ─────────┐
                            ├──→ Task 6 (CI workflow)
Task 3 (前端 lint 配置)  ──┤
        ↓                   │
Task 4 (前端 vitest)  ─────┤
        ↓                   │
Task 5 (前端组件测试)  ────┘
```

Task 6 依赖 Task 1-5 完成（所有 lint 和 test 必须本地能跑通）。
Task 7 是验证和收尾。
