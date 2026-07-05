# 贡献指南

感谢你愿意改进 AI 数据分析与报告生成 Agent。

## 开始之前

- 功能建议和缺陷请先通过对应的 Issue 模板提交。
- 安全漏洞不要创建公开 Issue，请遵循 [安全政策](SECURITY.md)。
- 参与项目即表示你同意遵守 [行为准则](CODE_OF_CONDUCT.md)。

## 本地开发

1. Fork 仓库并从 `main` 创建功能分支。
2. 按 README 安装 Python 与 Node.js 依赖。
3. 保持改动聚焦，并为行为变更补充或更新测试。
4. 提交前运行：

```bash
python -m pytest backend/tests -q
cd frontend
npm ci
npm run build
```

## Pull Request

- 使用清晰的标题说明改动目的。
- 在描述中关联 Issue，并说明实现方式和验证结果。
- 不要提交密钥、真实业务数据、数据库、上传文件或生成报告。
- 界面变更请附截图；API 或行为变更请同步更新文档与测试。
- 确保 GitHub Actions 检查全部通过。

提交贡献即表示你同意按本项目 MIT License 授权该贡献。
