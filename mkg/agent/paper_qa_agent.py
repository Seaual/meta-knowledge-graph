"""
Paper QA Agent - 回答论文内容相关问题
"""

import os
from typing import Dict, Any, Optional
from .prompts import PAPER_QA_PROMPT


class PaperQAAgent:
    """论文内容问答 Agent"""

    def __init__(self, llm_client, db, pdf_parser=None):
        """
        初始化 Paper QA Agent

        Args:
            llm_client: LLM 客户端
            db: Database 实例
            pdf_parser: PDFParser 实例（可选，用于读取全文）
        """
        self.llm_client = llm_client
        self.db = db
        self.pdf_parser = pdf_parser

        # 简单问题关键词（基于元数据回答）
        self.simple_keywords = [
            '讲什么', '关于什么', '摘要', '关键词', '作者',
            '发表', '期刊', '会议', '年份', '标题',
            '是什么', '简介', '概述',
        ]

    def answer(self, question: str, paper_doi: str) -> Dict[str, Any]:
        """
        回答关于论文的问题

        Args:
            question: 用户问题
            paper_doi: 论文 DOI

        Returns:
            包含回答的字典
        """
        # 获取论文信息
        paper = self.db.get_paper(paper_doi)
        if not paper:
            return {'error': f'未找到论文: {paper_doi}'}

        # 判断问题类型
        is_simple = self._is_simple_question(question)

        if is_simple and self._has_metadata(paper):
            # 基于存储的元数据回答
            return self._answer_from_metadata(question, paper)
        else:
            # 读取 PDF 全文回答
            return self._answer_from_fulltext(question, paper)

    def _is_simple_question(self, question: str) -> bool:
        """判断是否是简单问题"""
        question_lower = question.lower()
        return any(kw in question_lower for kw in self.simple_keywords)

    def _has_metadata(self, paper: Dict) -> bool:
        """检查论文是否有足够的元数据"""
        return bool(paper.get('abstract') or paper.get('title'))

    def _answer_from_metadata(self, question: str, paper: Dict) -> Dict[str, Any]:
        """基于元数据回答"""
        # 构建上下文
        context = f"""论文信息：
标题：{paper.get('title', '未知')}
作者：{', '.join(paper.get('authors') or [])}
发表年份：{paper.get('year', '未知')}
期刊/会议：{paper.get('venue', '未知')}
关键词：{', '.join(paper.get('keywords') or [])}
引用数：{paper.get('citation_count', 0)}

摘要：
{paper.get('abstract', '无摘要')}
"""
        if paper.get('tldr'):
            context += f"\nTL;DR: {paper['tldr']}"

        prompt = PAPER_QA_PROMPT.format(
            question=question,
            context=context,
            paper_title=paper.get('title', '未知'),
        )

        try:
            response = self.llm_client.generate(prompt)
            return {
                'answer': response,
                'source': 'metadata',
                'paper_title': paper.get('title'),
            }
        except Exception as e:
            return {'error': f'回答生成失败: {str(e)}'}

    def _answer_from_fulltext(self, question: str, paper: Dict) -> Dict[str, Any]:
        """读取 PDF 全文回答"""
        pdf_path = paper.get('pdf_path')
        if not pdf_path or not os.path.exists(pdf_path):
            # 回退到元数据回答
            if self._has_metadata(paper):
                return self._answer_from_metadata(question, paper)
            return {'error': '无法访问论文全文'}

        try:
            # 读取 PDF 全文
            from mkg.pdf_parser import PDFParser
            if not self.pdf_parser:
                self.pdf_parser = PDFParser()

            full_text = self.pdf_parser.extract_text(pdf_path)

            # 截取前 10000 字符（避免过长）
            if len(full_text) > 10000:
                full_text = full_text[:10000] + '...(内容过长，已截断)'

            context = f"""论文信息：
标题：{paper.get('title', '未知')}
作者：{', '.join(paper.get('authors') or [])}

论文内容：
{full_text}
"""
            prompt = PAPER_QA_PROMPT.format(
                question=question,
                context=context,
                paper_title=paper.get('title', '未知'),
            )

            response = self.llm_client.generate(prompt)
            return {
                'answer': response,
                'source': 'fulltext',
                'paper_title': paper.get('title'),
            }

        except Exception as e:
            return {'error': f'读取论文失败: {str(e)}'}

    def format_response(self, result: Dict[str, Any]) -> str:
        """格式化响应"""
        if 'error' in result:
            return result['error']

        answer = result.get('answer', '')
        source = result.get('source', 'metadata')
        source_note = '（基于论文摘要）' if source == 'metadata' else '（基于论文全文）'

        return f"{answer}\n\n_{source_note}_"