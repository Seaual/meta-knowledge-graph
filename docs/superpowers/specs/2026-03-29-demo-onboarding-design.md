# Demo 图谱与首次引导设计

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让新用户打开页面第一秒就能看到可交互的知识图谱，并通过引导弹窗了解如何配置 LLM 来处理自己的论文。

**Architecture:**
1. 预置 Demo 数据库（10篇LLM经典论文的概念图谱），首次启动时自动加载
2. 前端检测首次访问，显示功能介绍弹窗引导用户配置 LLM

**Tech Stack:** SQLite, React, TypeScript, localStorage

---

## 1. Demo 图谱数据

### 1.1 论文列表

10 篇 LLM 领域经典论文（按时间排序）：

| 年份 | 论文 | 引用数 | 核心概念 |
|------|------|--------|----------|
| 2017 | Attention is All you Need | 171,010 | Transformer, Self-Attention |
| 2019 | BERT | 112,171 | 预训练, 双向编码 |
| 2019 | GPT-2 | 27,847 | 自回归生成 |
| 2020 | GPT-3 | 55,895 | Few-shot Learning |
| 2021 | LoRA | 17,561 | 参数高效微调 |
| 2022 | InstructGPT | 19,358 | RLHF, 指令对齐 |
| 2022 | Chain-of-Thought | 16,698 | 思维链提示 |
| 2022 | FlashAttention | 3,886 | 高效注意力 |
| 2023 | LLaMA | 19,101 | 开源大模型 |
| 2023 | QLoRA | 4,159 | 量化微调 |

### 1.2 概念层级

```
人工智能 (field)
└── 自然语言处理 (direction)
    ├── 语言模型 (subdirection)
    │   ├── Transformer (method) → Self-Attention (technique) → FlashAttention (method)
    │   ├── GPT系列 (method) → GPT-2, GPT-3 (method)
    │   └── LLaMA (method)
    ├── 预训练方法 (subdirection) → BERT (method)
    ├── 指令微调 (subdirection)
    │   ├── RLHF (method)
    │   └── 参数高效微调 (technique) → LoRA (method) → QLoRA (method)
    └── 提示工程 (subdirection) → Chain-of-Thought (method)
```

**统计：**
- 概念节点：19 个
- 层级关系：18 条
- 论文-概念关联：52 条

### 1.3 数据存储

- 预置数据库文件：`data/mkg-demo.db`
- Docker 镜像内置，首次启动时复制为工作数据库

---

## 2. 首次访问引导弹窗

### 2.1 触发条件

```typescript
// 检测首次访问
const isFirstVisit = !localStorage.getItem('mkg_onboarding_dismissed');
```

### 2.2 弹窗内容

**标题：** 欢迎使用 Meta Knowledge Graph

**副标题：** 这是一个演示图谱，包含 10 篇 LLM 经典论文

**功能卡片（4个）：**

| 图标 | 功能 | 说明 |
|------|------|------|
| 📄 | PDF 上传 | 上传论文 PDF，自动提取元数据 |
| 🧠 | 概念提取 | LLM 自动构建概念层级 |
| 📊 | 图谱交互 | 拖拽、缩放、点击探索关系 |
| 🔍 | 研究点发现 | 基于图谱结构发现潜在研究方向 |

**提示文案：** "要处理你自己的论文，请先在设置页面配置 LLM API Key"

**按钮：**
- [关闭] — 关闭弹窗，标记已读
- [前往设置] — 跳转 Settings 页面并关闭弹窗

### 2.3 关闭行为

```typescript
// 关闭时标记
localStorage.setItem('mkg_onboarding_dismissed', 'true');
```

---

## 3. 实现要点

### 3.1 Demo 数据加载逻辑

**docker/start.sh 修改：**

```bash
# 如果数据库不存在，使用 demo 数据
if [ ! -f /app/data/mkg.db ]; then
    if [ -f /app/data/mkg-demo.db ]; then
        cp /app/data/mkg-demo.db /app/data/mkg.db
        echo "Initialized with demo data"
    else
        # 创建空数据库
        python -c "from mkg.database import Database; ..."
    fi
fi
```

### 3.2 弹窗组件

**新建文件：** `frontend/src/components/OnboardingModal.tsx`

**Props：**
- `open: boolean` — 是否显示
- `onClose: () => void` — 关闭回调
- `onGoToSettings: () => void` — 前往设置回调

**样式：**
- 居中模态框，半透明背景遮罩
- 响应式设计，移动端适配
- 动画：淡入淡出

### 3.3 入口集成

**修改文件：** `frontend/src/App.tsx` 或 `frontend/src/pages/Home.tsx`

```typescript
const [showOnboarding, setShowOnboarding] = useState(false);

useEffect(() => {
  const dismissed = localStorage.getItem('mkg_onboarding_dismissed');
  if (!dismissed) {
    setShowOnboarding(true);
  }
}, []);

// 渲染弹窗
<OnboardingModal
  open={showOnboarding}
  onClose={() => setShowOnboarding(false)}
  onGoToSettings={() => {
    setShowOnboarding(false);
    navigate('/settings');
  }}
/>
```

---

## 4. 文件变更清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `scripts/generate_demo_data.py` | 已创建 | Demo 数据生成脚本 |
| `data/mkg-demo.db` | 新增 | 预置 Demo 数据库 |
| `docker/start.sh` | 修改 | 添加 demo 数据加载逻辑 |
| `Dockerfile` | 修改 | 复制 demo 数据到镜像 |
| `frontend/src/components/OnboardingModal.tsx` | 新增 | 引导弹窗组件 |
| `frontend/src/pages/Home.tsx` | 修改 | 集成弹窗触发逻辑 |

---

## 5. 验收标准

1. ✅ 新用户打开页面，能看到预置的 LLM 概念图谱
2. ✅ 首次访问显示引导弹窗，展示 4 个功能卡片
3. ✅ 点击"关闭"后弹窗消失，刷新页面不再显示
4. ✅ 点击"前往设置"跳转到 Settings 页面
5. ✅ 用户上传自己的论文后，与 demo 数据共存