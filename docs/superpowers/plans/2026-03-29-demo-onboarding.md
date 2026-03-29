# Demo 图谱与首次引导实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新用户打开页面第一秒看到可交互的 LLM 概念图谱，并通过引导弹窗了解如何配置 LLM。

**Architecture:**
1. Demo 数据库打包进 Docker 镜像，首次启动自动加载
2. 前端首次访问检测 + 功能介绍弹窗组件

**Tech Stack:** SQLite, React, TypeScript, localStorage, Docker

---

## File Structure

| 文件 | 职责 |
|------|------|
| `data/mkg-demo.db` | 预置 Demo 数据库（已生成） |
| `docker/start.sh` | 启动脚本，检测并加载 demo 数据 |
| `Dockerfile` | 复制 demo 数据到镜像 |
| `frontend/src/components/OnboardingModal.tsx` | 引导弹窗组件 |
| `frontend/src/pages/Home.tsx` | 首页，集成弹窗触发 |

---

### Task 1: 修改 Docker 启动脚本加载 Demo 数据

**Files:**
- Modify: `docker/start.sh`

- [ ] **Step 1: 更新 start.sh 添加 demo 数据加载逻辑**

```bash
#!/bin/bash
set -e

echo "Starting Meta Knowledge Graph..."

# Create directories if they don't exist
mkdir -p /app/papers/pending /app/papers/processed /app/data

# Initialize database - load demo if first run
if [ ! -f /app/data/mkg.db ]; then
    echo "Initializing database..."
    if [ -f /app/data/mkg-demo.db ]; then
        echo "Loading demo data..."
        cp /app/data/mkg-demo.db /app/data/mkg.db
        echo "Demo database loaded (10 LLM papers with concept graph)"
    else
        python -c "
from mkg.database import Database
db = Database('/app/data/mkg.db')
db.connect()
print('Empty database initialized')
db.close()
"
    fi
else
    echo "Database exists, skipping initialization"
fi

# Start the backend (which also serves frontend in Docker mode)
cd /app
exec python -m uvicorn backend.main:app --host 0.0.0.0 --port 8088
```

- [ ] **Step 2: Commit**

```bash
git add docker/start.sh
git commit -m "feat(docker): auto-load demo database on first run"
```

---

### Task 2: 修改 Dockerfile 复制 Demo 数据

**Files:**
- Modify: `Dockerfile`

- [ ] **Step 1: 在 Dockerfile 中添加 demo 数据复制**

找到 `# Create data directories` 部分，在其之前添加：

```dockerfile
# Copy demo database
COPY data/mkg-demo.db /app/data/mkg-demo.db
```

完整修改后的相关部分：

```dockerfile
# Copy built frontend from stage 1
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Copy demo database
COPY data/mkg-demo.db /app/data/mkg-demo.db

# Create data directories
RUN mkdir -p /app/papers/pending /app/papers/processed /app/data
```

- [ ] **Step 2: Commit**

```bash
git add Dockerfile
git commit -m "feat(docker): include demo database in image"
```

---

### Task 3: 创建引导弹窗组件

**Files:**
- Create: `frontend/src/components/OnboardingModal.tsx`

- [ ] **Step 1: 创建 OnboardingModal.tsx**

```tsx
import { X, FileUp, Brain, Network, Search, Settings } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

interface Props {
  onClose: () => void
}

const FEATURES = [
  {
    icon: FileUp,
    title: 'PDF 上传',
    description: '上传论文 PDF，自动提取元数据'
  },
  {
    icon: Brain,
    title: '概念提取',
    description: 'LLM 自动构建概念层级'
  },
  {
    icon: Network,
    title: '图谱交互',
    description: '拖拽、缩放、点击探索关系'
  },
  {
    icon: Search,
    title: '研究点发现',
    description: '基于图谱结构发现潜在研究方向'
  }
]

export default function OnboardingModal({ onClose }: Props) {
  const navigate = useNavigate()

  const handleClose = () => {
    localStorage.setItem('mkg_onboarding_dismissed', 'true')
    onClose()
  }

  const handleGoToSettings = () => {
    localStorage.setItem('mkg_onboarding_dismissed', 'true')
    onClose()
    navigate('/settings')
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-lg w-full overflow-hidden">
        {/* Header */}
        <div className="bg-brand-gradient p-6 text-center relative">
          <button
            onClick={handleClose}
            className="absolute top-4 right-4 text-white/70 hover:text-white transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
          <div className="text-4xl mb-2">🎉</div>
          <h2 className="text-xl font-bold text-white">欢迎使用 Meta Knowledge Graph</h2>
          <p className="text-white/80 text-sm mt-2">
            这是一个演示图谱，包含 10 篇 LLM 经典论文
          </p>
        </div>

        {/* Features */}
        <div className="p-6">
          <div className="grid grid-cols-2 gap-4 mb-6">
            {FEATURES.map((feature, i) => (
              <div
                key={i}
                className="flex items-start gap-3 p-3 bg-brand-fill rounded-xl"
              >
                <div className="h-8 w-8 bg-brand-button rounded-lg flex items-center justify-center flex-shrink-0">
                  <feature.icon className="h-4 w-4 text-white" />
                </div>
                <div>
                  <p className="font-medium text-brand-700 text-sm">{feature.title}</p>
                  <p className="text-xs text-brand-500 mt-0.5">{feature.description}</p>
                </div>
              </div>
            ))}
          </div>

          {/* Tip */}
          <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 mb-6">
            <p className="text-sm text-amber-800">
              💡 <strong>提示：</strong>要处理你自己的论文，请先在设置页面配置 LLM API Key
            </p>
          </div>

          {/* Buttons */}
          <div className="flex gap-3">
            <button
              onClick={handleClose}
              className="flex-1 px-4 py-2.5 border border-gray-300 rounded-xl text-gray-700 hover:bg-gray-50 transition-colors"
            >
              关闭
            </button>
            <button
              onClick={handleGoToSettings}
              className="flex-1 px-4 py-2.5 bg-brand-button text-white rounded-xl hover:opacity-90 transition-opacity flex items-center justify-center gap-2"
            >
              <Settings className="h-4 w-4" />
              前往设置
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/OnboardingModal.tsx
git commit -m "feat(frontend): add onboarding modal component"
```

---

### Task 4: 在首页集成弹窗触发

**Files:**
- Modify: `frontend/src/pages/Home.tsx`

- [ ] **Step 1: 导入 OnboardingModal 组件**

在文件顶部添加导入：

```tsx
import OnboardingModal from '../components/OnboardingModal'
```

- [ ] **Step 2: 添加弹窗状态管理**

在 `Home` 组件内，`const [showS2Modal, setShowS2Modal] = useState(false)` 之后添加：

```tsx
const [showOnboarding, setShowOnboarding] = useState(false)
```

- [ ] **Step 3: 添加首次访问检测 useEffect**

在现有的 `useEffect` 之后添加：

```tsx
// Check first visit for onboarding
useEffect(() => {
  const dismissed = localStorage.getItem('mkg_onboarding_dismissed')
  if (!dismissed) {
    setShowOnboarding(true)
  }
}, [])
```

- [ ] **Step 4: 渲染弹窗组件**

在 `{/* S2 Config Modal */}` 块之后添加：

```tsx
{/* Onboarding Modal */}
{showOnboarding && (
  <OnboardingModal onClose={() => setShowOnboarding(false)} />
)}
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Home.tsx
git commit -m "feat(frontend): integrate onboarding modal on home page"
```

---

### Task 5: 移动 demo 数据到 data 目录

**Files:**
- Move: `mkg-demo.db` → `data/mkg-demo.db`

- [ ] **Step 1: 创建 data 目录并移动文件**

```bash
mkdir -p data
mv mkg-demo.db data/mkg-demo.db
```

- [ ] **Step 2: 更新 .gitignore（如需要）**

确保 `data/` 目录不会被忽略（因为我们需要追踪 demo 数据）。

检查 `.gitignore` 中是否有 `data/` 或 `*.db` 规则需要排除：

```bash
# 如果 .gitignore 忽略了 data/，需要添加例外
# 在 .gitignore 中添加：
!data/mkg-demo.db
```

- [ ] **Step 3: Commit**

```bash
git add data/mkg-demo.db
git commit -m "chore: move demo database to data directory"
```

---

### Task 6: 测试验证

**Files:**
- Test: Manual testing

- [ ] **Step 1: 清除 localStorage**

打开浏览器开发者工具，在 Console 中执行：
```javascript
localStorage.removeItem('mkg_onboarding_dismissed')
```

- [ ] **Step 2: 刷新首页，验证弹窗显示**

- 弹窗应居中显示
- 显示 4 个功能卡片
- 点击"关闭"后弹窗消失
- 刷新页面不再显示

- [ ] **Step 3: 测试"前往设置"按钮**

- 再次清除 localStorage
- 刷新页面
- 点击"前往设置"
- 应跳转到 `/settings` 页面

- [ ] **Step 4: 测试 Docker 构建（可选）**

```bash
cd docker
docker-compose build
docker-compose up -d
# 访问 http://localhost:8088 验证 demo 数据已加载
```

- [ ] **Step 5: 最终 commit**

```bash
git add -A
git commit -m "feat: complete demo onboarding feature"
```

---

## Summary

| Task | Description | Files |
|------|-------------|-------|
| 1 | Docker 启动脚本加载 demo | `docker/start.sh` |
| 2 | Dockerfile 复制 demo 数据 | `Dockerfile` |
| 3 | 创建引导弹窗组件 | `frontend/src/components/OnboardingModal.tsx` |
| 4 | 首页集成弹窗触发 | `frontend/src/pages/Home.tsx` |
| 5 | 移动 demo 数据到正确位置 | `data/mkg-demo.db` |
| 6 | 测试验证 | Manual testing |