# 真实 Markdown 测试素材

这个目录存放用于翻译测试的真实 Markdown 文档。`test_fixtures_structure.py`
会用 FakeProvider 把**每一篇**（含本 README）跑完整管线做离线结构校验；
需要验证真实译文质量时，用下面的命令联网跑。

## 素材清单

| 文件 | 代表场景 | 覆盖语法 |
| ---- | -------- | -------- |
| `code-walkthrough.md` | 技术教程 | 多语言 fenced code、行内代码、嵌套列表、链接 |
| `rich-syntax.md` | 语法大杂烩 | 表格对齐、任务列表、删除线、嵌套引用、脚注文本、图片、自动链接、emoji、水平线 |
| `docs-frontmatter.md` | 带 front matter 的文档 | YAML 头、行内/块级 LaTeX 公式、mermaid 图 |
| `readme-style.md` | 典型 README | 徽章图片、HTML 注释、代码块、许可证链接 |
| `api-reference.md` | API 文档 | 参数表、锚点链接、有序列表、路径占位符 |
| `zh-blog.md` | 中文源文（中→英方向） | 中文标点、引用、表格、代码块 |

## 联网真实翻译（人工验证用）

```bash
# 整个目录翻成中文（结构、产物齐全）
.venv/bin/mdtx translate src/test/fixtures/markdown --to zh-CN --output output/fixtures

# 单篇 + LLM-as-judge 质量评估
.venv/bin/mdtx translate src/test/fixtures/markdown/rich-syntax.md --to zh-CN --eval
```

需要 config（`~/.mdtx/config.yaml`）里配好可用的 provider。

## 新增素材

直接放入 `*.md` 文件即可，离线结构测试会自动覆盖。保持篇幅短小；
想覆盖的语法越冷门越好。
