# 极简 LLM 配置设计

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 简化 LLM 配置为极简模式，用户只需填写 URL、API Key、模型名称三个字段，系统自动识别兼容类型。

---

## 设计背景

当前配置方案存在以下问题：
1. 服务商列表过多（10+ 个），用户选择困难
2. 配置流程复杂，需要选择服务商 → API Key → URL → 模型
3. 大部分用户只需要填入自定义 URL 和 Key

## 解决方案

### 核心原则
1. **极简主义**：只保留 2 个选项 - Claude CLI 和自定义配置
2. **自动化**：系统根据 URL 自动判断 OpenAI/Anthropic 兼容类型
3. **通用性**：支持任何 OpenAI 或 Anthropic 兼容的服务

---

## 界面设计

### 配置类型选择

用户打开配置弹窗后，首先选择配置类型：

```
┌─────────────────────────────────┐
│  LLM 配置                        │
├─────────────────────────────────┤
│  配置类型                         │
│  ○ Claude Code CLI (本地开发)    │
│  ● 自定义配置                     │
└─────────────────────────────────┘
```

### 自定义配置表单

选择"自定义配置"后显示：

```
┌─────────────────────────────────┐
│  Base URL *                      │
│  ┌─────────────────────────────┐│
│  │ https://api.openai.com/v1   ││
│  └─────────────────────────────┘│
│  支持 OpenAI/Anthropic 官方 API 及兼容服务 │
│                                  │
│  API Key *                       │
│  ┌─────────────────────────────┐│
│  │ sk-••••••••                 ││
│  └─────────────────────────────┘│
│                                  │
│  模型名称 *                       │
│  ┌─────────────────────────────┐│
│  │ gpt-4o-mini                 ││
│  └─────────────────────────────┘│
│                                  │
│  [测试连接]  [保存配置]           │
└─────────────────────────────────┘
```

### 兼容类型自动判断

**判断规则：**
- URL 包含 "anthropic"（不区分大小写）→ Anthropic 兼容
- 其他所有情况 → OpenAI 兼容（默认）

**示例：**
- `https://api.anthropic.com` → Anthropic 兼容
- `https://api.minimaxi.com/anthropic` → Anthropic 兼容
- `https://api.openai.com/v1` → OpenAI 兼容
- `https://api.deepseek.com/v1` → OpenAI 兼容

---

## 后端设计

### 服务商列表

**backend/routes/llm.py - PROVIDERS 列表简化为：**

```python
PROVIDERS = [
    {
        "value": "claude_cli",
        "label": "Claude Code CLI（本地开发）",
        "requires_api_key": False,
        "models": []
    },
    {
        "value": "custom",
        "label": "自定义配置",
        "requires_api_key": True,
        "requires_base_url": True,
        "models": []
    }
]
```

### API 端点（保持不变）

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/llm/providers` | GET | 获取服务商列表 |
| `/api/llm/config` | GET | 获取当前配置 |
| `/api/llm/config` | POST | 保存配置 |
| `/api/llm/test` | POST | 测试连接 |

### LiteLLM 集成

**mkg/pdf_parser.py - LiteLLMClient 处理自定义配置：**

```python
def _get_litellm_model(self) -> str:
    """转换为 LiteLLM 模型格式"""
    # 自定义配置：根据 base_url 判断兼容类型
    if self.provider == 'custom':
        if self.base_url and 'anthropic' in self.base_url.lower():
            return f"anthropic/{self.model}"
        else:
            # 默认使用 OpenAI 格式
            return f"openai/{self.model}"

    # LiteLLM 格式：provider/model
    if '/' in self.model:
        return self.model
    return f"{self.provider}/{self.model}"
```

---

## 前端设计

### 组件修改

**frontend/src/components/LLMConfigModal.tsx：**

主要修改：
1. 删除服务商下拉选择器
2. 添加配置类型单选按钮（Claude CLI / 自定义配置）
3. 自定义配置显示 3 个输入框（URL、API Key、模型名称）
4. 移除"智能检测"按钮

**状态管理：**
```typescript
const [configType, setConfigType] = useState<'claude_cli' | 'custom'>('custom')
```

**条件渲染：**
```tsx
{/* 配置类型选择 */}
<div className="flex gap-2">
  <button onClick={() => setConfigType('claude_cli')}>
    Claude Code CLI
  </button>
  <button onClick={() => setConfigType('custom')}>
    自定义配置
  </button>
</div>

{/* 自定义配置表单 */}
{configType === 'custom' && (
  <>
    <input label="Base URL" />
    <input label="API Key" />
    <input label="模型名称" />
  </>
)}
```

---

## 数据库设计

保持现有表结构不变，已支持自定义配置：

```sql
CREATE TABLE llm_provider_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    config_id INTEGER NOT NULL,
    provider TEXT NOT NULL,  -- 'claude_cli' 或 'custom'
    api_key TEXT,
    base_url TEXT,
    model TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    ...
);
```

---

## 实现任务

### Task 1: 后端简化
- [ ] 修改 `backend/routes/llm.py` - PROVIDERS 列表只保留 2 个选项
- [ ] 确保 `LiteLLMClient` 正确处理 `custom` provider
- [ ] 测试 URL 自动判断逻辑

### Task 2: 前端重构
- [ ] 修改 `LLMConfigModal.tsx` - 删除服务商下拉，改为单选按钮
- [ ] 简化配置表单为 3 个字段
- [ ] 删除智能检测相关代码
- [ ] 更新 API 调用逻辑

### Task 3: 测试验证
- [ ] 测试 Claude CLI 配置
- [ ] 测试自定义配置（OpenAI 兼容）
- [ ] 测试自定义配置（Anthropic 兼容）
- [ ] 测试配置保存和读取

---

## 配置流程

```
用户点击 "LLM 配置"
    ↓
弹窗打开
    ↓
选择配置类型
    ├─ Claude CLI → 无需配置，直接使用
    └─ 自定义配置 → 填写 URL/API Key/模型
              ↓
         点击"测试连接"
              ↓
         后端根据 URL 判断兼容类型
              ↓
         测试成功 → 点击"保存配置"
              ↓
         配置持久化到数据库
```

---

## 错误处理

| 场景 | 处理方式 |
|------|----------|
| URL 格式错误 | 提示"请输入有效的 URL" |
| API Key 无效 | 提示"API Key 无效，请检查后重试" |
| 模型不存在 | 提示"模型不存在，请确认模型名称" |
| 网络连接失败 | 提示"网络连接失败，请检查 URL 或网络设置" |
| 兼容类型判断失败 | 默认使用 OpenAI 兼容 |

---

## 兼容性说明

### 支持的服务

**OpenAI 兼容格式：**
- OpenAI 官方 API
- DeepSeek、Moonshot、通义千问等第三方服务
- Gemini（通过代理）

**Anthropic 兼容格式：**
- Anthropic 官方 API
- MiniMax 的 Anthropic 端点

### 迁移路径

已有配置数据迁移：
- `provider='openai'` → `provider='custom'`（保留 URL 和 Key）
- `provider='deepseek'` → `provider='custom'`
- 其他服务商同理

---

## 成功标准

1. ✓ 用户配置步骤从 4 步减少到 3 步
2. ✓ 服务商选项从 10+ 个减少到 2 个
3. ✓ 系统自动正确判断兼容类型（准确率 > 95%）
4. ✓ 所有现有功能正常工作（论文解析、概念提取、去重）