![Free-Markdown-Translator](https://socialify.git.ci/CrazyMayfly/Free-Markdown-Translator/image?custom_description=Free+Markdown+Translator%E6%98%AF%E4%B8%80%E6%AC%BE%E5%9F%BA%E4%BA%8E+AI+Agent+%E6%B5%81%E6%B0%B4%E7%BA%BF%E7%9A%84+Markdown+%E6%96%87%E6%A1%A3%E7%BF%BB%E8%AF%91%E5%99%A8&description=1&font=Bitter&forks=1&language=1&name=1&owner=1&pattern=Solid&stargazers=1&theme=Auto)

[English](docs/README.english.md) |  [Deutsch](docs/README.german.md) | [日本語](docs/README.japanese.md) | [русский](docs/README.russian.md) | [한국어](docs/README.korean.md) | [Português](docs/README.portuguese.md) | [Español](docs/README.spanish.md) | [Français](docs/README.french.md) | [हिन्दी](docs/README.hindi.md) | [العربية](docs/README.arabic.md)

# Free Markdown Translator

Free Markdown Translator 是一个基于 AI Agent 流水线的 Markdown 文档翻译工具，可以将Mardown文档翻译为任意语言（40+种），在翻译过程中尽量**保留原始 Markdown 文档结构**，同时能够很好地**保持语义连贯性**。

## 🚀 主要功能和特性

AI Agent 流水线翻译 + AST 语法树校验：**格式稳定、语义连贯、成本可控**。核心能力按领域归纳如下（详细机制见[执行流程](#-执行流程与机制)）：

| 领域 | 能力 |
| --- | --- |
| 🈯️ 术语一致 | 译前抽取术语表、译后自动修正漂移译法；持久化术语库跨运行累积，人工条目优先于模型投票（API `/api/glossary` 可管理） |
| 🔗 上下文连贯 | 分包对齐章节边界（表格不拆包）；每包携带文档大纲、术语表与前一包摘要；锚点调度为并行包注入真实已译文本；翻译模型可**主动请求更深的记忆检索**（拉取式上下文）；文内锚点链接自动跟随译后标题 |
| ✅ 质量保障 | 反思式审校（批评 → 修复 → 复核）；零成本语义哨兵（占位符/数字守恒、长度比）拦截丢内容；quality 模式**文档级终审**（跨章节指代/衔接/语气漂移）；`--eval` LLM-as-judge 打分并把弱段移出记忆；`--regression` 黄金样例回归 |
| 💰 成本效率 | 翻译记忆：相同段落零调用复用、相似段落模糊复用或作 few-shot 示例；`--resume` 断点续传；asyncio 并发 + 限流退避 |
| 🧱 结构稳定 | Structured Outputs 受限解码（端点不支持自动降级）、截断精确识别；代码/URL/表格/标题占位符保护；校验失败自动格式修复 |
| 🔌 灵活集成 | 任意 OpenAI 兼容端点（OpenRouter / DeepSeek / Ollama / vLLM…）；审校与评审可配置独立模型；`--serve` MCP 模式接入 AI 客户端；桌面应用 + Web UI |

其他：多目标语言、目录递归翻译、文风与保留术语自定义、快速/平衡/严格三档模式。

## 🖥️ 桌面应用（Tauri + Vue3）

`mdtx` 附带一个本地桌面工作台：架构是 Tauri 2 壳 + Vue3 前端 + Python FastAPI sidecar（复用完整翻译管线），仅监听 `127.0.0.1`，不依赖任何云服务。

### 下载安装

到 [Releases](https://github.com/CrazyMayfly/Free-Markdown-Translator/releases) 下载对应平台安装包（由 GitHub Actions 自动构建发布）：

| 平台 | 产物 |
|------|------|
| macOS (Apple Silicon) | `mdtx_3.0.0_aarch64.dmg`（未签名，首次打开需右键 → 打开） |
| Windows x64 | `mdtx_3.0.0_x64-setup.exe` |
| Ubuntu/Debian | `mdtx_3.0.0_amd64.deb`（另有通用 `AppImage`） |

首次启动后在「配置」页填入 base_url / API Key / 模型（可用「测试连接」验证），即可开始翻译。

### 界面预览

| 新建任务（拖拽 / 多选 / 语言与模式） | 任务记录（本地持久化 · 再来一次） |
|---|---|
| ![新建任务](docs/screenshots/submit.png) | ![任务记录](docs/screenshots/jobs.png) |

| 翻译结果（渲染视图 · 一键复制/保存/访达） | 分段对照（段落级人工修订） |
|---|---|
| ![翻译结果](docs/screenshots/result.png) | ![分段对照](docs/screenshots/segments.png) |

| 配置（端点测试 · 文风术语 · 翻译记忆） | |
|---|---|
| ![配置](docs/screenshots/config.png) | |

### 功能一览

- **新建任务**：访达拖拽 / 文件浏览器多选文件或整个目录（按 `*.md` 递归收集）、语言标签多选、快速/平衡/严格模式、断点续传
- **实时进度**：任务 × 翻译对双层进度、bundle 级进度条、token 用量实时累计（含前缀缓存命中）、SSE 事件流；多文件 × 多语言任务自动并行执行
- **任务记录**：所有任务持久化到本机（`~/.mdtx/history.sqlite3`），重启应用不丢；支持「再来一次」按原参数重新提交、删除记录
- **结果页**：渲染视图 / 分段对照双视图；段落级人工修订（保存后自动同步整篇译文）；一键复制译文、保存到文件、在访达中显示；LLM 质量评估四维评分条
- **写失败保护**：输出文件写入失败时译文不丢失，结果页可一键手动保存
- **系统通知**：任务在后台完成/失败时弹系统通知
- **配置管理**：表单化编辑 `~/.mdtx/config.yaml`（API Key 掩码显示、不回显）、一键测试模型端点连通性（延迟 + 模型列表）、翻译记忆统计与清空

### 本地开发

开发模式（三种，按需选择）：

```bash
# 1. 纯浏览器开发：终端 1 起 API，终端 2 起 vite（vite 代理 /api → 8000）
mdtx --ui-port 8000
cd ui && npm install && npm run dev     # 打开 http://localhost:5173

# 2. Tauri 桌面窗口（自动带起 vite 与 Python API）
cd ui && npx tauri dev

# 3. 正式打包（.app / .dmg，内嵌 PyInstaller sidecar）
.venv/bin/python src/buildtool/build_api.py   # 先构建 mdtx-api sidecar
cd ui && npx tauri build
```

环境要求：Node ≥18（nvm 安装即可）、Rust stable（rustup）、Python 依赖 `pip install -e ".[ui]"`。

### 发布流程

三个平台的安装包由 GitHub Actions 自动构建：推送 `v*` 标签即触发（`.github/workflows/release.yml`），矩阵覆盖 macOS arm64 / Windows x64 / Ubuntu x64，构建产物自动挂到对应 Release。也可以在 Actions 页面手动触发 `workflow_dispatch` 只出产物不发布。

## ⚡ Quick Start

### 方式一：Clone 仓库后启动

```bash
git clone https://github.com/CrazyMayfly/Free-Markdown-Translator.git
cd Free-Markdown-Translator
pip install -r requirements.txt
python src/cli/main.py --init-config 
```

也可以安装为本地命令（推荐，之后可直接使用 `mdtx`）：

```bash
pip install -e .
mdtx --init-config
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
.\mdtx.exe docs --to Chinese --mode quality
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

翻译并做质量评估（LLM-as-judge 四维打分）：

```bash
.\mdtx.exe README.md --to Chinese --eval
```

从中断处续传（已完成的翻译包直接复用）：

```bash
.\mdtx.exe docs --to Chinese --resume
```

## 🤖 作为 MCP 工具供 AI 客户端调用

安装 MCP 支持并以 stdio 方式启动服务：

```bash
pip install "mdtx[mcp]"
mdtx --serve
```

在 ZCode / Claude Desktop / Cursor 等支持 MCP 的客户端中配置：

```json
{
  "mcpServers": {
    "mdtx": {
      "command": "mdtx",
      "args": ["--serve"]
    }
  }
}
```

之后 AI 客户端即可调用两个工具：

- `translate_markdown(path, target_langs, mode?, tone?, model?, write?)`：翻译 Markdown 文件，返回各语言的译文、校验结果与 token 用量，翻译进度通过 MCP 进度通知上报
- `evaluate_translation(path, target_lang)`：翻译并用 LLM-as-judge 打分（准确度/流畅度/术语/格式）

## 🔌 兼容的模型服务

任何 OpenAI 兼容的 chat 接口都可以通过 `base_url` 接入：

| 服务 | base_url 示例 | 说明 |
|------|--------------|------|
| OpenAI | `https://api.openai.com/v1` | 默认；完整支持 Structured Outputs |
| OpenRouter | `https://openrouter.ai/api/v1` | 聚合多家模型 |
| DeepSeek | `https://api.deepseek.com/v1` | |
| Ollama（本地） | `http://localhost:11434/v1` | 不支持 json_schema 时自动降级 |
| vLLM（本地） | `http://localhost:8000/v1` | 同上 |

`provider.name` 仅为标识，可填任意值；实际端点由 `base_url` 决定。配置 `structured_outputs: auto`（默认）时，端点不支持受限解码会自动回退到 `json_object` 模式。

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
  # fast: 省 token/提速（不跑 LLM 审校/终审）；balanced: 默认（只审可疑包）；quality: 最高质量（全量审校 + 终审，strict 为兼容别名）。
  mode: balanced
  # 可选模型路由（留空 = provider.model）。
  fast_model: ""
  quality_model: ""
  brief_model: ""
  # 强制开启审校 Agent。关闭时，balanced 只审可疑包，quality 全量审校。
  enable_review: false
  # 强制开启格式修复 Agent。关闭时，balanced/quality 遇到校验失败仍可能触发修复。
  enable_format_guard: false
  # 输出校验失败时是否直接报错。
  fail_on_validation_error: true

# 分段策略。先按 Markdown 结构（标题/列表/表格/引用）打包，超长块再按行拆分。
# 预算单位是估算 token 而非字符：同样 6000 字符，中文约 4200 token、英文约 1800 token。
segmentation:
  # 单个文本包的硬上限（估算源 token），也是超长块按行拆分的阈值。
  max_bundle_tokens: 4000
  # 小章节/尾包合并到该 token 数为止；0 表示不合并。
  min_bundle_tokens: 1000

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
3. `DocumentContextBuilder` 生成文档摘要、标题大纲（heading_outline）、风格约束、术语上下文
4. `GlossaryAgent` 译前抽取文档术语表（term → 译法），与持久化术语库、preserve_terms 合并后注入每个 bundle 的上下文
5. `Orchestrator` 把 segment 组织成多个 bundle：优先在标题处对齐章节边界、同一表格的单元格不拆包，控制每次模型调用的大小
6. **翻译记忆**查询：同一文档内完全相同的段落直接复用；高度相似的历史段落模糊复用；较相似的作为 few-shot 示例注入（置信度低于阈值的条目不复用）
7. **锚点-并行混合调度**：每章首个 bundle 先按文档顺序串行翻译，其余 bundle 并行执行并携带锚点 bundle 的真实已译文本
8. `TranslatorAgent` 对每个 bundle 进行翻译（Structured Outputs 强约束输出格式，上下文含文档大纲、术语表、前一 bundle 摘要、锚点译文与相似段落示例）；模型对看不准的段落可返回 `context_requests`，管线做更深的记忆检索后重译一轮（拉取式上下文，fast 模式关闭）
9. **确定性语义哨兵**：占位符/数字守恒与长度比检查，发现丢内容/幻觉即强制审校该 bundle 并记录到输出报告
10. `ReviewerAgent` 反思式审校：先输出结构化批评意见，再仅对达到严重度阈值的段落做针对性改进并复核（`fast` 关闭 / `balanced` medium 及以上 / `quality` 全量；修复时携带相邻段落上下文）
11. **术语一致性 pass**：聚合各 bundle 上报的 `applied_terms`，检测同一术语的译法漂移，按权威术语表自动改写受影响段落并回写持久化术语库
12. **文档级终审**（`quality` 模式）：`EditorAgent` 以全文为审阅单元检查跨包话语流（指代悬空、衔接生硬、术语/语气漂移），仅修正被标记段落且携带文档序邻居上下文
13. `MarkdownRenderer` 将翻译结果重新映射回 AST 并渲染为 Markdown；文内 `](#锚点)` 链接自动改指译后标题
14. `MarkdownValidator` 校验 front matter 和整体结构
15. 如果校验失败，`FormatGuardAgent` 会并发尝试修复格式问题
16. 译文写入翻译记忆并更新断点状态，最终输出翻译后的 Markdown 和可选报告文件

## 🗂️ 项目结构

```text
src/
├─ agents/        Agent 定义与提示词，负责翻译、审校、评估、术语协调、格式保护
├─ api/           FastAPI 服务层：任务管理、SSE 进度、配置/记忆路由（UI 后端）
├─ cli/           命令行入口与参数处理
├─ core/          流水线、任务编排、核心数据结构
├─ infra/         配置加载与日志基础设施
├─ llm/           模型客户端（同步/异步）、Provider 封装、Schema
├─ mcp_server/    MCP server，把翻译能力暴露为 AI 客户端工具
├─ memory/        文档上下文、翻译记忆、断点续传
├─ parser/        Markdown 解析、AST 映射、渲染、分段
├─ validators/    front matter 与结构校验
├─ buildtool/     打包脚本（Windows exe / macOS sidecar）与资源
└─ ui 的 Tauri+Vue 工程位于 ui/（前端 ui/src、桌面壳 ui/src-tauri）
```

## Star History

<a href="https://star-history.com/#CrazyMayfly/Free-Markdown-Translator&Date">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=CrazyMayfly/Free-Markdown-Translator&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=CrazyMayfly/Free-Markdown-Translator&type=Date" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=CrazyMayfly/Free-Markdown-Translator&type=Date" />
 </picture>
</a>
