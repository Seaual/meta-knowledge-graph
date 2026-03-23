# 概念页面放射状分层布局设计

**日期**: 2026-03-23
**状态**: 草案

## 概述

将概念页面从当前的力导向布局改为放射状分层布局，以更好地展示概念的层级关系（field > direction > subdirection > task > method > technique）。

## 当前状态

- 使用 d3-force 力导向算法布局
- 所有概念节点自由散布
- 节点大小基于 paper_count 和 degree（连接数）
- 支持点击高亮连接节点、双击进入详情视图

## 目标设计

### 布局结构

**放射状层级 + 虚拟中心 + 混合模式**

```
                    L0 (field)
                      ○
                     /|\
                    / | \
                   /  |  \
              L1   ○   ○   ○   (direction)
                  /|   |   |\
                 / |   |   | \
             L2 ○  ○   ○   ○  ○  (subdirection)
               /|   |   |   |\
          L3  ○ ○   ○   ○   ○ ○  (task)
             /|               |\
        L4  ○ ○               ○ ○  (method)
           /                     \
      L5  ○                       ○  (technique)
```

**核心要素：**

1. **虚拟中心点**：画布中央的虚拟节点，所有根概念围绕它排列
2. **同心环**：6 个同心环，每个环对应一个层级
   - 环 0（最内层）：L0 field（领域）
   - 环 1：L1 direction（方向）
   - 环 2：L2 subdirection（子方向）
   - 环 3：L3 task（任务）
   - 环 4：L4 method（方法）
   - 环 5（最外层）：L5 technique（技术）
3. **扇区分组**：每个根概念（field）占据一个扇区，其子概念在扇区内展开

### 视觉设计

**节点样式：**

| 层级 | 基础半径 | 透明度 | 说明 |
|------|----------|--------|------|
| L0 | 18px | 100% | 最大最醒目 |
| L1 | 14px | 95% | 较大 |
| L2 | 11px | 85% | 中等 |
| L3 | 9px | 75% | 较小 |
| L4 | 7px | 65% | 小 |
| L5 | 5px | 55% | 最小，可选择性显示 |

节点颜色沿用现有的 CATEGORY_CONFIG：

```typescript
const CATEGORY_CONFIG = {
  field: { color: '#FF6B6B', bgColor: '#FEE2E2' },
  direction: { color: '#4ECDC4', bgColor: '#CCFBF1' },
  subdirection: { color: '#45B7D1', bgColor: '#E0F2FE' },
  task: { color: '#96CEB4', bgColor: '#DCFCE7' },
  method: { color: '#FFA726', bgColor: '#FFEDD5' },
  technique: { color: '#FFD93D', bgColor: '#FEF9C3' },
}
```

**扇区背景：**

- 每个根概念扇区使用对应颜色的 20% 透明度填充
- 扇区边界用虚线标记
- 悬停时扇区背景加深

**环线：**

- 同心环用浅灰色虚线绘制
- 可选择显示/隐藏

### 交互设计

#### 1. 层级筛选器

**UI 位置**：左上角信息面板下方

**控件**：
- 范围滑块：选择显示的最小层级和最大层级
- 快捷按钮：「概览 (L0-L2)」「标准 (L0-L4)」「全部 (L0-L5)」

**行为**：
- 调整滑块时，超出范围的节点淡出消失
- 边仅显示两端节点都在范围内的边

#### 2. 点击钻取

**触发**：单击任意概念节点

**行为**：
1. 选中的节点移动到画布中心
2. 布局重新计算，只显示该节点的子树
3. 面包屑导航显示当前路径（如：计算机科学 > 组合优化 > 车辆路径问题）
4. 「返回」按钮返回上一级或全局视图

**退出钻取**：
- 点击面包屑导航
- 点击「返回概览」按钮
- 点击空白区域

#### 3. 悬停高亮

**触发**：鼠标悬停在节点上

**行为**：
1. 悬停节点的完整路径高亮（从根到叶的所有祖先和后代）
2. 路径上的边加粗、着色
3. 其他节点和边变淡（opacity: 0.2）
4. 显示 tooltip：节点名称、层级、论文数量

**取消悬停**：鼠标移出节点区域

### 详情面板

**触发**：双击节点（保留现有行为）

**内容**：
- 概念名称、层级标签
- 论文数量
- 父概念列表（可点击跳转）
- 子概念列表（可点击跳转）
- 关联论文列表

### 布局算法

**核心参数**：

```typescript
interface RadialLayoutConfig {
  center: { x: number; y: number }  // 画布中心
  ringRadius: number[]              // 每层环的半径 [60, 120, 180, 240, 300, 360]
  sectorAngle: number               // 扇区角度（根据根概念数量动态计算）
  nodeSpacing: number               // 同层节点间距
}
```

**算法步骤**：

1. **计算根概念位置**：
   - 获取所有无父节点的概念作为根概念
   - 均匀分布在第一环上

2. **分配扇区**：
   - 每个根概念分配一个扇区
   - 扇区角度 = 360° / 根概念数量

3. **布局子概念**：
   - 递归遍历每个根概念的子概念
   - 子概念在对应层级的环上，位于父概念的扇区内
   - 同一父概念下的子概念在扇区内均匀分布

4. **绘制边**：
   - 仅绘制父子关系边
   - 边使用贝塞尔曲线平滑连接

**实现方式**：

使用 d3-hierarchy 的 radial tree 布局，结合自定义的扇区约束：

```typescript
import { hierarchy, tree } from 'd3-hierarchy'

function computeRadialLayout(
  concepts: Concept[],
  edges: GraphEdge[],
  config: RadialLayoutConfig
): Map<string, { x: number; y: number }> {
  // 1. 构建层次结构
  const roots = findRoots(concepts, edges)
  const nodeMap = new Map(concepts.map(c => [c.id, c]))

  // 2. 为每个根构建树
  const positions = new Map<string, { x: number; y: number }>()

  roots.forEach((root, rootIndex) => {
    const sectorStart = (rootIndex / roots.length) * 2 * Math.PI
    const sectorEnd = ((rootIndex + 1) / roots.length) * 2 * Math.PI

    // 3. 递归布局子节点
    layoutSubtree(root, config.center, sectorStart, sectorEnd, 0, positions, nodeMap)
  })

  return positions
}
```

### 数据需求

**后端 API 需提供**：

1. 概念的层级深度（depth）
2. 概念的父子关系（现有 edges 已提供）
3. 根概念列表（无父节点的概念）

**现有 API 可复用**：
- `GET /api/concepts/` - 概念列表
- `GET /api/graph/` - 图数据（nodes + edges）
- `GET /api/concepts/{id}` - 概念详情

**可能需要新增**：
- `GET /api/concepts/roots` - 根概念列表
- 或在前端从现有数据中计算

### 文件变更

| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `frontend/src/pages/Concepts.tsx` | 重写 | 主要布局和交互逻辑 |
| `frontend/src/lib/radialLayout.ts` | 新增 | 放射状布局算法 |
| `frontend/src/components/LevelFilter.tsx` | 新增 | 层级筛选器组件 |
| `frontend/src/components/Breadcrumb.tsx` | 新增 | 面包屑导航组件 |

### 性能考虑

- 使用 React Flow 的 `onlyRenderVisibleElements` 优化渲染
- 节点数量 > 200 时，外层节点默认隐藏
- 使用 `useMemo` 缓存布局计算结果
- 层级筛选时使用 CSS opacity 过渡，避免重新挂载组件

### 兼容性

- 保留现有的详情视图（双击进入论文视图）
- 保留现有的小地图、缩放、平移功能
- 图例增加层级说明

## 验收标准

1. 放射状布局正确显示 6 层概念层级
2. 扇区按根概念正确分组
3. 层级筛选器可正常过滤显示范围
4. 点击钻取可进入子树视图并可返回
5. 悬停高亮正确显示路径
6. 现有功能（详情面板、缩放、小地图）正常工作
7. 性能：100+ 节点时无明显卡顿