---
name: frontend-react-best-practices
description: |
  Activate when writing, reviewing, or refactoring React components.
  Handles: performance optimization, bundle size reduction, component composition, hook patterns.
  Keywords: react, component, hook, performance, memo, bundle, optimization.
  Do NOT use for: backend code review (use code-reviewer), CSS styling (use dedicated style guides).
  # Source: sergiodxa/agent-skills@frontend-react-best-practices
allowed-tools: [Read, Edit]
---

# React Best Practices Skill

React 性能优化和组合模式指南，包含 33 条规则，覆盖 Bundle 优化、渲染性能、Hooks 和组合模式。

## 适用场景

- 编写新的 React 组件
- 审查代码中的性能问题
- 重构现有 React 代码
- 优化打包体积
- 处理 hooks 和状态

## 规则分类

### Bundle Size Optimization（关键）

#### bundle-barrel-imports

避免从 barrel 文件导入，直接从源文件导入。

```tsx
// Bad: 加载整个库 (200-800ms)
import { Check, X } from "lucide-react";

// Good: 只加载需要的
import Check from "lucide-react/dist/esm/icons/check";
import X from "lucide-react/dist/esm/icons/x";
```

#### bundle-conditional

仅在功能激活时加载模块。

```tsx
useEffect(() => {
  if (enabled && typeof window !== "undefined") {
    import("./heavy-module").then((mod) => setModule(mod));
  }
}, [enabled]);
```

#### bundle-preload

在 hover/focus 时预加载，提升感知速度。

```tsx
<button
  onMouseEnter={() => import("./editor")}
  onFocus={() => import("./editor")}
  onClick={openEditor}
>
  Open Editor
</button>
```

### Re-render Optimization（重要）

#### rerender-functional-setstate

使用函数式 setState 保持回调稳定。

```tsx
// Bad: 闭包风险，依赖 items 变化
const addItem = useCallback(
  (item) => {
    setItems([...items, item]);
  },
  [items],
);

// Good: 总是使用最新状态，稳定引用
const addItem = useCallback((item) => {
  setItems((curr) => [...curr, item]);
}, []);
```

#### rerender-derived-state-no-effect

在渲染期间派生状态，不要在 effect 中。

```tsx
// Bad: 额外状态和 effect，额外渲染
const [fullName, setFullName] = useState("");
useEffect(() => {
  setFullName(firstName + " " + lastName);
}, [firstName, lastName]);

// Good: 渲染期间直接派生
const fullName = firstName + " " + lastName;
```

#### rerender-lazy-state-init

为昂贵的初始值传递函数给 useState。

```tsx
// Bad: 每次渲染都执行 expensiveComputation()
const [data] = useState(expensiveComputation());

// Good: 只在初始渲染执行
const [data] = useState(() => expensiveComputation());
```

#### rerender-dependencies

在 effect 中使用原始类型依赖。

```tsx
// Bad: user 任何字段变化都会触发
useEffect(() => {
  console.log(user.id);
}, [user]);

// Good: 只在 id 变化时触发
useEffect(() => {
  console.log(user.id);
}, [user.id]);
```

#### rerender-memo

将昂贵计算提取到 memoized 组件中。

```tsx
const UserAvatar = memo(function UserAvatar({ user }) {
  let id = useMemo(() => computeAvatarId(user), [user]);
  return <Avatar id={id} />;
});

function Profile({ user, loading }) {
  if (loading) return <Skeleton />;
  return <UserAvatar user={user} />;
}
```

### Rendering Performance（重要）

#### rendering-conditional-render

数字条件渲染使用三元运算符，不要用 &&。

```tsx
// Bad: count 为 0 时渲染 "0"
{
  count && <Badge>{count}</Badge>;
}

// Good: count 为 0 时不渲染
{
  count > 0 ? <Badge>{count}</Badge> : null;
}
```

#### rendering-hoist-jsx

将静态 JSX 提取到组件外部。

```tsx
// Good: 重用相同元素
const skeleton = <div className="animate-pulse h-20 bg-gray-200" />;

function Container({ loading }) {
  return loading ? skeleton : <Content />;
}
```

### Hooks（高优先级）

#### hooks-limit-useeffect

只在绝对必要时使用 useEffect。

```tsx
// Bad: 用 effect 派生状态
let [filtered, setFiltered] = useState(items);
useEffect(() => {
  setFiltered(items.filter((i) => i.active));
}, [items]);

// Good: 渲染期间派生
let filtered = items.filter((i) => i.active);

// Good: 如果昂贵则用 useMemo
let filtered = useMemo(() => items.filter((i) => i.active), [items]);
```

#### hooks-useeffect-named-functions

在 useEffect 中使用命名函数，便于调试。

```tsx
// Bad: 匿名箭头函数
useEffect(() => {
  document.title = title;
}, [title]);

// Good: 命名函数
useEffect(
  function syncDocumentTitle() {
    document.title = title;
  },
  [title],
);
```

### Composition Patterns（高优先级）

#### composition-avoid-boolean-props

不要用布尔 prop 自定义行为，使用组合。

```tsx
// Bad: 布尔 prop 爆炸
<Composer isThread isEditing={false} showAttachments />

// Good: 显式变体
<ThreadComposer channelId="abc" />
<EditComposer messageId="xyz" />
```

#### composition-compound-components

将复杂组件结构化为复合组件。

```tsx
<Composer.Provider state={state} actions={actions}>
  <Composer.Frame>
    <Composer.Input />
    <Composer.Footer>
      <Composer.Submit />
    </Composer.Footer>
  </Composer.Frame>
</Composer.Provider>
```

#### composition-explicit-variants

创建显式变体组件而非 prop 组合。

```tsx
function ThreadComposer({ channelId }) {
  return (
    <ThreadProvider channelId={channelId}>
      <Composer.Frame>
        <Composer.Input />
        <AlsoSendToChannelField />
        <Composer.Submit />
      </Composer.Frame>
    </ThreadProvider>
  );
}
```

## 使用方式

在代码审查或重构时，对照这些规则检查：

1. **Bundle 优化**：检查导入方式、懒加载
2. **渲染优化**：检查 memo、useMemo、useCallback 使用
3. **Hooks**：检查 useEffect 是否必要
4. **组合**：检查组件 API 设计

## 输出格式

审查结果以 Markdown 格式输出：

```markdown
## React 代码审查报告

### Bundle 优化
- [ ] `lucide-react` 使用 barrel 导入 → 建议直接导入

### 渲染性能
- [ ] `List` 组件缺少 memo → 添加 React.memo
- [ ] `useEffect` 依赖对象 → 改用原始值

### 建议
1. ...
2. ...
```

## 完成标准

- [ ] 检查所有 Bundle 相关规则
- [ ] 检查渲染性能规则
- [ ] 检查 Hooks 使用
- [ ] 提供具体改进建议

## 错误处理

| 情况 | 处理方式 |
|-----|---------|
| 无法确定规则适用性 | 标注为"需人工确认" |
| 规则冲突 | 记录冲突，让用户决定 |