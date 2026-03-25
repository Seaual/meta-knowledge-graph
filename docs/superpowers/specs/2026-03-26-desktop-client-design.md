---
name: Desktop Client with Tauri + PyO3
description: Package meta-knowledge-graph as a Windows desktop application using Tauri 2.0 + PyO3 + PyOxidizer
type: project
---

# Windows 桌面客户端设计

## 目标

将 meta-knowledge-graph 打包为 Windows 桌面客户端，支持公开分发，单进程架构，用户自选数据目录。

## 技术选型

| 组件 | 技术 | 版本 |
|------|------|------|
| 前端框架 | Tauri 2.0 | 2.x |
| 前端 UI | React + Vite | 复用现有 |
| Python 嵌入 | PyO3 | 0.22+ |
| Python 打包 | PyOxidizer | 最新 |
| 安装程序 | NSIS | 3.x |
| 自动更新 | Tauri Updater | 内置 |

## 目录结构

```
app/
├── src-tauri/              # Tauri Rust 代码
│   ├── src/
│   │   ├── main.rs         # 入口，初始化 Python
│   │   ├── python.rs       # PyO3 调用 Python
│   │   ├── commands.rs     # Tauri IPC 命令
│   │   └── config.rs       # 配置管理
│   ├── Cargo.toml
│   ├── tauri.conf.json
│   └── icons/
├── src-python/             # Python 代码
│   ├── pyproject.toml      # Python 依赖
│   ├── mkg/                # 核心 Python 模块
│   └── backend/            # FastAPI 路由
├── frontend/               # 前端代码（符号链接到根目录 frontend/）
└── pyoxidizer.bzl          # PyOxidizer 打包配置
```

## 数据存储

**首次启动流程**：
1. 应用启动 → 检查 `%AppData%\MKG\config.json` 是否存在
2. 若不存在 → 弹出目录选择对话框
3. 用户选择目录 → 创建数据结构并保存配置
4. 进入主界面

**数据目录结构**：
```
<用户选择的目录>/
├── mkg.db              # SQLite 数据库
├── papers/             # PDF 文件存储
│   ├── pending/
│   └── processed/
└── exports/            # 导出文件
```

**配置文件**（`%AppData%\MKG\config.json`）：
```json
{
  "dataDir": "D:\\MyDocuments\\MKGData",
  "version": "1.0.0",
  "autoUpdate": true,
  "startWithWindows": false
}
```

## 架构设计

### 进程模型

单进程架构：Tauri (Rust) 通过 PyO3 直接调用 Python 代码，无需子进程管理。

```
┌─────────────────────────────────────┐
│           Tauri Application          │
├─────────────────────────────────────┤
│  Rust Runtime (WebView + Native)    │
│  ├── Frontend (React/HTML/CSS)      │
│  ├── Commands (IPC)                 │
│  └── PyO3 Bridge                    │
├─────────────────────────────────────┤
│  Embedded Python (PyOxidizer)       │
│  ├── mkg/ (核心模块)                 │
│  └── backend/ (API 路由)            │
└─────────────────────────────────────┘
```

### API 调用方式

传统 FastAPI 路由转换为 Tauri Commands：

```rust
// Rust 侧
#[tauri::command]
async fn process_paper(doi: String, state: State<'_, PythonState>) -> Result<ProcessResponse, String> {
    Python::with_gil(|py| {
        let mkg = state.module.import(py, "mkg.graph")?;
        let result = mkg.call_method1("process_paper", (doi,))?;
        Ok(result.extract()?)
    })
}
```

```python
# Python 侧 (mkg/graph.py)
def process_paper(doi: str) -> dict:
    # 复用现有逻辑
    ...
```

## 自动更新

**更新检查流程**：
1. 应用启动时请求 `https://api.github.com/repos/<user>/mkg/releases/latest`
2. 比较版本号
3. 若有新版本 → 下载 `.msi` 或更新包
4. 安装并重启

**GitHub Releases 结构**：
```
MKG_1.0.0_x64.msi           # 安装程序
MKG_1.0.0_x64_portable.zip  # 便携版
latest.json                  # 版本元数据
```

**Tauri Updater 配置**（`tauri.conf.json`）：
```json
{
  "plugins": {
    "updater": {
      "endpoints": ["https://<domain>/updates/{{target}}/{{arch}}/{{current_version}}"],
      "pubkey": "<公钥>"
    }
  }
}
```

## 安装程序

**NSIS 脚本功能**：
- 用户选择安装位置
- 创建桌面快捷方式（可选）
- 添加到开始菜单
- 开机自启动选项（可选）
- 卸载程序

**安装包内容**：
```
MKG/
├── MKG.exe              # 主程序（包含嵌入的 Python）
├── resources/           # 前端资源
├── LICENSE
└── README.txt
```

## 实现阶段

### 阶段 1: 基础架构（1 天）

**目标**：搭建 Tauri + PyO3 项目骨架

**任务**：
1. 创建 `app/` 目录
2. 初始化 Tauri 项目
3. 配置 PyO3 依赖
4. 实现简单的 Python 调用示例
5. 配置前端符号链接

**验证**：能启动应用，点击按钮调用 Python 函数返回结果

### 阶段 2: 功能集成（1.5 天）

**目标**：复用现有前后端代码

**任务**：
1. 迁移 Python 后端代码到 `src-python/`
2. 将 FastAPI 路由转换为 Tauri Commands
3. 调整前端 API 调用（fetch → tauri.invoke）
4. 实现数据目录选择逻辑
5. 集成数据库初始化

**验证**：完整的论文上传、处理、查看功能

### 阶段 3: PyOxidizer 打包（1 天）

**目标**：将 Python 嵌入到最终二进制文件

**任务**：
1. 编写 `pyoxidizer.bzl` 配置
2. 配置 Python 依赖打包
3. 测试打包后的应用
4. 优化包体积

**验证**：独立 exe 文件，无需 Python 环境即可运行

### 阶段 4: 安装程序与分发（0.5 天）

**目标**：生成可分发的安装包

**任务**：
1. 编写 NSIS 安装脚本
2. 配置应用图标
3. 测试安装/卸载流程
4. 配置 GitHub Actions 自动构建

**验证**：用户可通过安装程序安装使用

### 阶段 5: 自动更新（可选，0.5 天）

**目标**：支持自动更新

**任务**：
1. 配置 Tauri Updater
2. 生成签名密钥对
3. 编写版本发布脚本
4. 测试更新流程

**验证**：发布新版本后，用户应用能自动更新

## 依赖清单

**Rust (Cargo.toml)**：
```toml
[dependencies]
tauri = { version = "2", features = ["updater"] }
pyo3 = { version = "0.22", features = ["auto-initialize"] }
serde = { version = "1", features = ["derive"] }
serde_json = "1"
tokio = { version = "1", features = ["full"] }
```

**Python (pyproject.toml)**：
```toml
[project]
dependencies = [
    "fastapi",
    "sqlalchemy",
    "pypdf",
    "anthropic",
    "google-generativeai",
    "openai",
    "pypinyin",
]
```

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| PyOxidizer 打包复杂 | 开发延期 | 先用简单配置，逐步优化 |
| PyO3 版本兼容 | 功能异常 | 锁定 Python 3.11，充分测试 |
| 包体积过大 | 用户体验差 | 精简依赖，排除不需要的包 |
| 杀毒软件误报 | 用户流失 | 申请代码签名证书 |

## 成功标准

1. 用户无需安装 Python 环境即可使用
2. 首次启动可选择数据存储位置
3. 完整保留现有功能
4. 安装包小于 150MB
5. 支持自动更新