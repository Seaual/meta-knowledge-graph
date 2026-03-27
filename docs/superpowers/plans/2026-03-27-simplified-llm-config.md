# 极简 LLM 配置实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 简化 LLM 配置为极简模式，用户只需选择 Claude CLI 或填写 URL/API Key/模型名称。

**Architecture:** 后端简化服务商列表为 2 个选项，前端改为单选按钮切换配置类型，移除复杂的服务商下拉选择。

**Tech Stack:** Python/FastAPI (后端), TypeScript/React (前端), LiteLLM (LLM 客户端)

---

## 文件结构

**修改文件：**
- `backend/routes/llm.py` - 简化 PROVIDERS 列表
- `frontend/src/components/LLMConfigModal.tsx` - 重构为单选按钮界面
- `mkg/pdf_parser.py` - 已支持 custom provider，无需修改

---

## Task 1: 后端简化

**Files:**
- Modify: `backend/routes/llm.py:33-102`

- [ ] **Step 1: 简化 PROVIDERS 列表**

将 PROVIDERS 列表替换为只有 2 个选项：

```python
# Available providers - 极简配置
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
    },
]
```

- [ ] **Step 2: 验证后端启动**

```bash
cd D:/meta-knowledge-graph-main
python -c "from backend.routes.llm import PROVIDERS; print(len(PROVIDERS))"
```

Expected: `2`

- [ ] **Step 3: 提交后端修改**

```bash
git add backend/routes/llm.py
git commit -m "refactor(llm): simplify providers to claude_cli and custom only"
```

---

## Task 2: 前端重构

**Files:**
- Modify: `frontend/src/components/LLMConfigModal.tsx`

- [ ] **Step 1: 添加 configType 状态**

在状态声明处添加：

```typescript
const [configType, setConfigType] = useState<'claude_cli' | 'custom'>('custom')
```

- [ ] **Step 2: 重写组件 JSX**

完整替换 return 语句中的内容：

```tsx
return (
  <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
    <div className="bg-white rounded-xl shadow-xl w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b">
        <h2 className="text-lg font-semibold">LLM 服务配置</h2>
        <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
          <X className="h-5 w-5" />
        </button>
      </div>

      {/* Content */}
      <div className="p-4 space-y-4">
        {/* Config Type Selection */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">配置类型</label>
          <div className="flex gap-2">
            <button
              onClick={() => {
                setConfigType('claude_cli')
                setConfigs([{ provider: 'claude_cli', is_active: true }])
                setTestResult(null)
              }}
              className={`flex-1 py-2 px-4 rounded-lg border text-sm font-medium ${
                configType === 'claude_cli' ? 'border-purple-500 bg-purple-50 text-purple-700' : 'border-gray-200 text-gray-600'
              }`}
            >
              Claude Code CLI
            </button>
            <button
              onClick={() => {
                setConfigType('custom')
                setConfigs([{ provider: 'custom', is_active: true }])
                setTestResult(null)
              }}
              className={`flex-1 py-2 px-4 rounded-lg border text-sm font-medium ${
                configType === 'custom' ? 'border-purple-500 bg-purple-50 text-purple-700' : 'border-gray-200 text-gray-600'
              }`}
            >
              自定义配置
            </button>
          </div>
        </div>

        {/* Claude CLI notice */}
        {configType === 'claude_cli' && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 text-sm text-yellow-700">
            <Check className="inline h-4 w-4 mr-1" />
            Claude Code CLI 仅限本地开发使用，Docker 环境不可用
          </div>
        )}

        {/* Custom Config Form */}
        {configType === 'custom' && (
          <>
            {/* Base URL */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Base URL <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={configs[0]?.base_url || ''}
                onChange={e => updateConfig(0, 'base_url', e.target.value)}
                placeholder="https://api.openai.com/v1"
                className={`w-full border rounded-lg px-3 py-2 text-sm ${!configs[0]?.base_url ? 'border-red-300' : ''}`}
              />
              <p className="text-xs text-gray-500 mt-1">支持 OpenAI/Anthropic 官方 API 及兼容服务</p>
            </div>

            {/* API Key */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                API Key <span className="text-red-500">*</span>
              </label>
              <input
                type="password"
                value={configs[0]?.api_key || ''}
                onChange={e => updateConfig(0, 'api_key', e.target.value)}
                placeholder="sk-..."
                className="w-full border rounded-lg px-3 py-2 text-sm"
              />
            </div>

            {/* Model Name */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                模型名称 <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={configs[0]?.model || ''}
                onChange={e => updateConfig(0, 'model', e.target.value)}
                placeholder="gpt-4o-mini, claude-3-5-sonnet-20241022..."
                className="w-full border rounded-lg px-3 py-2 text-sm"
              />
            </div>
          </>
        )}

        {/* Test Result */}
        {testResult && (
          <div className={`rounded-lg p-3 text-sm ${testResult.success ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`}>
            {testResult.message}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="flex gap-2 p-4 border-t bg-gray-50">
        <button
          onClick={handleTest}
          disabled={testing}
          className="flex-1 py-2 px-4 rounded-lg border border-gray-200 text-sm font-medium text-gray-600 hover:bg-gray-100 disabled:opacity-50"
        >
          {testing ? <Loader2 className="inline h-4 w-4 animate-spin mr-1" /> : null}
          测试连接
        </button>
        <button
          onClick={handleSave}
          disabled={saving}
          className="flex-1 py-2 px-4 rounded-lg bg-purple-600 text-white text-sm font-medium hover:bg-purple-700 disabled:opacity-50"
        >
          {saving ? '保存中...' : '保存配置'}
        </button>
      </div>
    </div>
  </div>
)
```

- [ ] **Step 3: 删除不需要的变量和逻辑**

删除以下不再使用的变量：
```typescript
// 删除这些
const [mode, setMode] = useState<'single' | 'per_function'>('single')
const [providers, setProviders] = useState<Provider[]>([])
const [_functionGroups, setFunctionGroups] = useState<any[]>([])
const currentProvider = providers.find(p => p.value === configs[0]?.provider)
const requiresApiKey = currentProvider?.requires_api_key ?? true
const requiresBaseUrl = currentProvider?.requires_base_url ?? false
const defaultBaseUrl = currentProvider?.default_base_url
const recommendedModels = currentProvider?.models || []
```

删除 useEffect 中的 providers 和 functionGroups 加载：
```typescript
useEffect(() => {
  // 只保留配置加载
  llmApi.getConfig().then(res => {
    if (res.data.providers?.length > 0) {
      const savedConfig = res.data.providers[0]
      setConfigs(res.data.providers)
      // 根据保存的 provider 设置 configType
      if (savedConfig.provider === 'claude_cli') {
        setConfigType('claude_cli')
      } else {
        setConfigType('custom')
      }
    }
  })
}, [])
```

更新 handleSave 函数：
```typescript
const handleSave = async () => {
  setSaving(true)
  try {
    const config = configs[0]
    await llmApi.saveConfig({ mode: 'single', providers: [config] })
    onSave()
  } catch (err) {
    alert('保存失败')
  } finally {
    setSaving(false)
  }
}
```

- [ ] **Step 4: 验证前端编译**

```bash
cd D:/meta-knowledge-graph-main/frontend
npm run build
```

Expected: Build successful without errors

- [ ] **Step 5: 提交前端修改**

```bash
git add frontend/src/components/LLMConfigModal.tsx
git commit -m "refactor(frontend): simplify LLM config to 2 options with radio buttons"
```

---

## Task 3: 测试验证

**Files:**
- Manual testing in browser

- [ ] **Step 1: 启动后端**

```bash
cd D:/meta-knowledge-graph-main
python -m uvicorn backend.main:app --reload --port 8000
```

- [ ] **Step 2: 启动前端**

```bash
cd D:/meta-knowledge-graph-main/frontend
npm run dev
```

- [ ] **Step 3: 测试 Claude CLI 配置**

操作：
1. 打开浏览器 http://localhost:5173
2. 点击 LLM 配置
3. 选择 "Claude Code CLI"
4. 验证显示黄色提示框
5. 点击测试连接

Expected: 测试成功

- [ ] **Step 4: 测试自定义配置 (OpenAI 兼容)**

操作：
1. 选择 "自定义配置"
2. Base URL: `https://api.openai.com/v1`
3. API Key: (填入有效 key)
4. 模型名称: `gpt-4o-mini`
5. 点击测试连接

Expected: 测试成功

- [ ] **Step 5: 测试自定义配置 (Anthropic 兼容)**

操作：
1. Base URL: `https://api.anthropic.com` (或包含 anthropic 的 URL)
2. API Key: (填入有效 key)
3. 模型名称: `claude-3-5-sonnet-20241022`
4. 点击测试连接

Expected: 测试成功，后端使用 anthropic/ 前缀

- [ ] **Step 6: 测试配置保存和读取**

操作：
1. 保存一个配置
2. 刷新页面
3. 再次打开 LLM 配置

Expected: 显示之前保存的配置

- [ ] **Step 7: 最终提交**

```bash
git add -A
git commit -m "feat: complete simplified LLM config implementation"
```

---

## 成功标准

- [x] 服务商选项从 10+ 个减少到 2 个
- [x] 配置界面简化为配置类型选择 + 3 个输入框
- [x] 系统根据 URL 自动判断 OpenAI/Anthropic 兼容类型
- [x] Claude CLI 配置正常工作
- [x] 自定义配置正常工作（支持两种兼容格式）
- [x] 配置保存和读取正常工作