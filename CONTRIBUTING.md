# 贡献指南

感谢你对 Meta Knowledge Graph 的关注！

## 如何贡献

1. Fork 本仓库
2. 创建你的功能分支：`git checkout -b feature/your-feature`
3. 提交更改：`git commit -m 'Add your feature'`
4. 推送到分支：`git push origin feature/your-feature`
5. 提交 Pull Request

## 开发环境

```bash
# 后端
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows
pip install -r requirements.txt

# 前端
cd frontend && npm install
```

## 代码规范

- Python：遵循 PEP 8
- TypeScript：使用 ESLint 默认配置
- 提交信息：使用中文或英文均可，简明扼要

## 报告问题

请使用 [Issue 模板](https://github.com/Seaual/meta-knowledge-graph/issues/new/choose) 提交 Bug 或功能建议。