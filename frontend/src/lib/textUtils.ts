// frontend/src/lib/textUtils.ts

/**
 * 移除文本中的思考标签内容
 * LLM 可能返回 alisation... 内容，这些应该被过滤掉
 */
export function removeThinkingTags(content: string): string {
  if (!content) return content

  // 移除 atisation... 标签
  let result = content.replace(/<tool_call>[\s\S]*?<\/think>/g, '')

  // 移除可能的其他思考标记（如 🤔 开头的行）
  result = result.replace(/🤔\s*[\s\S]*?(?=\n\n|\n[{`\[]|$)/g, '')

  return result.trim()
}

/**
 * 工具名称中文映射
 */
export const TOOL_LABELS: Record<string, string> = {
  analyze_research_points: '分析研究点',
  deep_research: '深入研究',
  search_paper: '搜索论文',
  get_paper_by_title: '获取论文详情',
  read_paper_content: '阅读论文内容',
  analyze_citations: '分析引用关系',
  get_concept_graph: '获取概念图谱',
  recommend_papers: '推荐相关论文',
  list_folders: '获取文件夹列表',
  move_paper_to_folder: '移动论文',
  create_folder: '创建文件夹',
}

/**
 * 获取工具的中文名称
 */
export function getToolLabel(toolName: string): string {
  return TOOL_LABELS[toolName] || toolName
}