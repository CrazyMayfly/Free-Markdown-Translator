![Free-Markdown-Translator](https://socialify.git.ci/CrazyMayfly/Free-Markdown-Translator/image?custom_description=Free+Markdown+Translator%E6%98%AF%E4%B8%80%E6%AC%BE%E5%9F%BA%E4%BA%8E+AI+Agent+%E6%B5%81%E6%B0%B4%E7%BA%BF%E7%9A%84+Markdown+%E6%96%87%E6%A1%A3%E7%BF%BB%E8%AF%91%E5%99%A8&description=1&font=Bitter&forks=1&language=1&name=1&owner=1&pattern=Solid&stargazers=1&theme=Auto)

[English](docs/README.english.md) |  [Deutsch](docs/README.german.md) | [日本語](docs/README.japanese.md) | [русский](docs/README.russian.md) | [한국어](docs/README.korean.md) | [Português](docs/README.portuguese.md) | [Español](docs/README.spanish.md) | [Français](docs/README.french.md) | [हिन्दी](docs/README.hindi.md) | [العربية](docs/README.arabic.md)

# Free Markdown Translator

Free Markdown Translator 是一个基于 AI Agent 流水线的 Markdown 文档翻译工具，可以将Mardown文档翻译为任意语言（40+种），在翻译过程中尽量**保留原始 Markdown 文档结构**，同时能够很好地**保持语义连贯性**。

## 🚀 主要功能和特性

- 使用 AI 驱动翻译流程以及AST语法树校验，可以保持**格式的稳定性**和**语意连贯性**
- 可以自定义语言风格，输入匹配，输出格式，支持不同的翻译模式（快速、平衡、严格）以适应不同需求
- 内置 `TranslatorAgent`、`ReviewerAgent`、`FormatGuardAgent`，分别负责翻译、审校和格式修复（按翻译模式启用）
- 支持 front matter、标题层级、列表、表格、代码块、链接等结构保护
- 提供结构校验与输出报告，帮助发现格式漂移和内容异常
- 兼容 OpenAI 风格接口，可接入 OpenAI 或其他兼容服务
- 支持多目标语言、目录递归翻译、并行处理、文风约束和术语保留

## ⚡ Quick Start

### 方式一：Clone 仓库后启动

```bash
git clone https://github.com/CrazyMayfly/Free-Markdown-Translator.git
cd Free-Markdown-Translator
pip install -r requirements.txt
python src/cli/main.py --init-config 
```

初始化后，默认配置文件会生成到：

```text
~/.mdtx/config.yaml
```

配置好 API Key 后即可开始翻译：

```bash
python src/cli/main.py README.md --to english,japanese
```

### 方式二：下载 exe 直接使用

如果你使用的是 Windows，也可以下载已经打包好的 `mdtx.exe` 后直接运行。首次使用建议先初始化配置：

```powershell
.\mdtx.exe --init-config
```

然后编辑：

```text
~/.mdtx/config.yaml
```

配置完成后即可执行：

```powershell
.\mdtx.exe README.md --to Chinese
```

### 常用场景命令示例

单文件翻译为中文：

```bash
.\mdtx.exe README.md --to Chinese
```

把整个 `doc` 目录递归翻译为英文和日文：

```bash
.\mdtx.exe doc --to english,japanese
```

指定输出目录：

```bash
.\mdtx.exe README.md --to Chinese --output translated
```

只匹配目录中指定文件名格式的 Markdown 文件 （使用正则匹配）：

```bash
.\mdtx.exe docs --to Chinese --match "*.md"
```

提高并行度，加快大批量翻译：

```bash
.\mdtx.exe docs --to Chinese --threads 10
```

开启更严格的翻译和校验流程，消耗更多token，花费更多时间但是获取更好的翻译效果：

```bash
.\mdtx.exe docs --to Chinese --mode strict
```

强制开启审校和格式保护：

```bash
.\mdtx.exe docs --to Chinese --review true --guard true
```

切换模型或文风：

```bash
.\mdtx.exe README.md --to Chinese --model gpt-5-mini --tone technical
```

输出详细日志，便于排查：

```bash
.\mdtx.exe --verbose README.md --to Chinese
```

## ⚙️ 配置说明

项目会按以下优先顺序查找配置文件：

1. `--config` 指定的路径
2. 仓库根目录下的 `config.yaml`
3. `src/config.yaml`
4. `~/.mdtx/config.yaml`

一个典型配置如下：

```yaml
# 目标语言列表。支持一次翻译为多个语言。
target_languages:
  - english
  - japanese

# 执行设置。
execution:
  # 全局 bundle 级最大并行翻译数。
  max_parallel_translations: 10
  
# 大模型服务配置。当前实现为 OpenAI 兼容接口。
provider:
  name: openai
  base_url: https://api.openai.com/v1
  # 推荐通过环境变量提供密钥；如需直填，可写在 api_key。
  api_key:
  api_key_env: OPENAI_API_KEY
  model: gpt-4o
  # 温度越低，输出越稳定。
  temperature: 0.2
  # 单次响应的最大 token 数。
  max_tokens: 8000

# 翻译流程控制。
pipeline:
  # fast: 更快（不做review和guard）；balanced: 默认（按条件触发review和guard）；strict: 更严格（执行review和guard）。
  mode: balanced
  # 强制开启审校 Agent。关闭时，balanced/strict 仍可能按条件触发审校。
  enable_review: false
  # 强制开启格式修复 Agent。关闭时，balanced/strict 遇到校验失败仍可能触发修复。
  enable_format_guard: false
  # 输出校验失败时是否直接报错。
  fail_on_validation_error: true

# 分段策略。控制一次发送给模型的文本包大小。
segmentation:
  max_bundle_chars: 6000
  max_bundle_segments: 36

# 输入规则。
input:
  # 当传入目录时，递归匹配需要翻译的文件。
  file_pattern: "*.md"

# 文风与术语约束，会注入翻译上下文。
style:
  tone: technical
  audience: developers
  # 不翻译的专有名词或术语列表，会注入上下文并在翻译过程中保护。
  preserve_terms:
    - OpenAI
    - Markdown
    - Python
  instructions:
    - Keep protected placeholders unchanged.
    - Do not alter Markdown control syntax.

# 输出设置。
output:
  # 所有翻译结果会输出到这个目录下，并尽量保留原目录层级。
  directory: output
  # 可用变量：{stem} 原文件名，{lang} 目标语言缩写。
  file_suffix_template: "{stem}.{lang}.md"
  # 是否同时写出 *.report.json 报告。
  write_report: false
```

### API Key 配置示例

推荐使用环境变量：

```powershell
$env:OPENAI_API_KEY="your-api-key"
.\mdtx.exe README.md --to Chinese
```

也可以写在配置文件中：

```yaml
provider:
  api_key: xxxxx
```

如果你使用兼容接口，也可以在 `config.yaml` 中修改：

```yaml
provider:
  name: openai
  base_url: https://your-openai-compatible-endpoint/v1
  api_key_env: YOUR_API_KEY_ENV
  model: your-model-name
```

## 🔄 执行流程与机制

1. `MarkdownParser` 先把源文档解析成 AST，识别 Markdown 结构
2. `SegmentExtractor` 从 AST 中提取可翻译片段，并保护占位符、控制语法等敏感内容
3. `DocumentContextBuilder` 生成文档摘要、风格约束、术语上下文
4. `Orchestrator` 按配置把 segment 组织成多个 bundle，控制每次模型调用的大小
5. `TranslatorAgent` 对每个 bundle 进行翻译
6. `ReviewerAgent` 在 `balanced` / `strict` 模式下按条件进行审校
7. `MarkdownRenderer` 将翻译结果重新映射回 AST 并渲染为 Markdown
8. `MarkdownValidator` 校验 front matter 和整体结构
9. 如果校验失败，`FormatGuardAgent` 会在需要时尝试修复格式问题
10. 最终输出翻译后的 Markdown 和可选报告文件

## 🗂️ 项目结构

```text
src/
├─ agents/        Agent 定义与提示词，负责翻译、审校、格式保护
├─ cli/           命令行入口与参数处理
├─ core/          流水线、任务编排、核心数据结构
├─ infra/         配置加载与日志基础设施
├─ llm/           模型客户端、Provider 封装、Schema
├─ memory/        文档上下文和翻译记忆相关组件
├─ parser/        Markdown 解析、AST 映射、渲染、分段
├─ validators/    front matter 与结构校验
└─ buildtool/     Windows exe 打包脚本与资源
```

## Star History

<a href="https://star-history.com/#CrazyMayfly/Free-Markdown-Translator&Date">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=CrazyMayfly/Free-Markdown-Translator&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=CrazyMayfly/Free-Markdown-Translator&type=Date" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=CrazyMayfly/Free-Markdown-Translator&type=Date" />
 </picture>
</a>
