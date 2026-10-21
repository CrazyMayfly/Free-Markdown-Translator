![Free-Markdown-Translator](https://socialify.git.ci/CrazyMayfly/Free-Markdown-Translator/image?custom_description=Free+Markdown+Translator%E6%98%AF%E4%B8%80%E6%AC%BE%E5%9F%BA%E4%BA%8E+AI+Agent+%E6%B5%81%E6%B0%B4%E7%BA%BF%E7%9A%84+Markdown+%E6%96%87%E6%A1%A3%E7%BF%BB%E8%AF%91%E5%99%A8&description=1&font=Bitter&forks=1&language=1&name=1&owner=1&pattern=Solid&stargazers=1&theme=Auto)

# Free Markdown Translator

Free Markdown Translator is a Markdown document translation tool powered by an AI Agent pipeline. It can translate Markdown documents into any language, focusing on preserving the original Markdown structure as much as possible during translation while maintaining semantic coherence. It is suitable for scenarios such as documentation sites, local knowledge bases, READMEs, multi-language technical documents, etc. ✨

## 🚀 Key Features and Capabilities

- 🧠 Utilizes an AI-driven translation workflow and AST syntax tree validation to ensure format stability and greater contextual consistency.
- ✂️ Customizable language style, input matching, and output format. Supports different translation modes (Fast, Balanced, Strict) to suit various requirements.
- 🤖 Built-in `TranslatorAgent`, `ReviewerAgent`, and `FormatGuardAgent`, responsible for translation, proofreading, and format repair respectively (enabled based on translation mode).
- 🧱 Supports structure protection for front matter, heading levels, lists, tables, code blocks, links, etc.
- ✅ Provides structure validation and output reports to help identify format drift and content anomalies.
- 🔌 Compatible with OpenAI-style interfaces, can connect to OpenAI or other compatible services.
- ⚙️ Supports multiple target languages, recursive directory translation, parallel processing, style constraints, and terminology preservation.

## ⚡ Quick Start

### Option 1: Clone the repository and start

```bash
git clone https://github.com/CrazyMayfly/Free-Markdown-Translator.git
cd Free-Markdown-Translator
pip install -r requirements.txt
python src/cli/main.py --init-config
```

After initialization, the default configuration file will be generated at:

```text
~/.mdtx/config.yaml
```

After configuring the API Key, you can start translating:

```bash
python src/cli/main.py README.md --to english,japanese
```

### Option 2: Download the exe and use directly

If you are using Windows, you can also download the packaged `mdtx.exe` and run it directly. It is recommended to initialize the configuration before first use:

```powershell
.\mdtx.exe --init-config
```

Then edit:

```text
~/.mdtx/config.yaml
```

After configuration is complete, you can execute:

```powershell
.\mdtx.exe README.md --to Chinese
```

### Common Scenario Command Examples

Translate a single file to Chinese:

```bash
.\mdtx.exe README.md --to Chinese
```

Recursively translate the entire `doc` directory to English and Japanese:

```bash
.\mdtx.exe doc --to english,japanese
```

Specify output directory:

```bash
.\mdtx.exe README.md --to Chinese --output translated
```

Only match Markdown files with specified filename formats in the directory (using regex matching):

```bash
.\mdtx.exe docs --to Chinese --match "name*.md"
```

Increase parallelism to speed up bulk translation:

```bash
.\mdtx.exe docs --to Chinese --threads 10
```

Enable a stricter translation and verification process, consuming more tokens and taking more time but yielding better translation results:

```bash
.\mdtx.exe docs --to Chinese --mode strict
```

Force enable proofreading and format protection:

```bash
.\mdtx.exe docs --to Chinese --review true --guard true
```

Switch model or writing style:

```bash
.\mdtx.exe README.md --to Chinese --model gpt-5-mini --tone technical
```

Output detailed logs for easier troubleshooting:

```bash
.\mdtx.exe --verbose README.md --to Chinese
```

## ⚙️ Configuration Instructions

The project will look for configuration files in the following priority order:

1. `--config`Path specified by `--config`
2.  in the repository root directory
3. `src/config.yaml`
4. `~/.mdtx/config.yaml`

A typical configuration is as follows:

```yaml
# List of target languages. Supports translation into multiple languages at once.
target_languages:
  - english
  - japanese
# Execution settings.
execution:
  # Global maximum number of parallel translations at the bundle level.
  max_parallel_translations: 10
# Large model service configuration. Currently implemented as an OpenAI-compatible interface.
provider:
  name: openai
  base_url: https://api.openai.com/v1
  # Recommended to provide the key via environment variable; if filling directly, can be written in api_key.
  api_key:
  api_key_env: OPENAI_API_KEY
  model: gpt-4o
  # The lower the temperature, the more stable the output.
  temperature: 0.2
  # Maximum number of tokens for a single response.
  max_tokens: 8000
# Translation pipeline control.
pipeline:
  # fast: Faster (without review and guard); balanced: Default (triggers review and guard based on conditions); strict: Stricter (executes review and guard).
  mode: balanced
  # Force enable Review Agent. When disabled, balanced/strict may still trigger review based on conditions.
  enable_review: false
  # Force enable Format Guard Agent. When disabled, balanced/strict may still trigger repair upon validation failure.
  enable_format_guard: false
  # Whether to report an error directly when output validation fails.
  fail_on_validation_error: true
# Segmentation strategy. Packs along Markdown structure (headings/lists/tables/quotes), then splits oversized blocks by line.
segmentation:
  max_bundle_tokens: 3000
  min_bundle_tokens: 800
# Input rules.
input:
  # When a directory is passed, recursively match files that need translation.
  file_pattern: "*.md"
# Style and terminology constraints, will be injected into the translation context.
style:
  tone: technical
  audience: developers
  # List of proper nouns or terms not to be translated, will be injected into context and protected during translation.
  preserve_terms:
    - OpenAI
    - Markdown
    - Python
  instructions:
    - Keep protected placeholders unchanged.
    - Do not alter Markdown control syntax.
# Output settings.
output:
  # All translation results will be output to this directory, preserving the original directory hierarchy as much as possible.
  directory: output
  # Available variables: {stem} original filename, {lang} target language abbreviation.
  file_suffix_template: "{stem}.{lang}.md"
  # Whether to write the *.report.json report simultaneously.
  write_report: false
```

### API Key Configuration Example

Using environment variables is recommended:

```powershell
$env:OPENAI_API_KEY="your-api-key"
.\mdtx.exe README.md --to Chinese
```

It can also be written in the configuration file (not recommended, poses security risks):

```yaml
provider:
  api_key: xxxxx
```

If you use a compatible interface, you can also modify it in `config.yaml`:

```yaml
provider:
  name: openai
  base_url: https://your-openai-compatible-endpoint/v1
  api_key_env: YOUR_API_KEY_ENV
  model: your-model-name
```

## 🔄 Execution Flow and Mechanism

This project does not 'feed the entire Markdown document to the model for translation at once', but instead employs a more robust pipeline:

1. `MarkdownParser` First, parse the source document into an AST to identify Markdown structure
2. `SegmentExtractor` Extract translatable segments from the AST, protecting sensitive content such as placeholders and control syntax
3. `DocumentContextBuilder` Generate document summary, style constraints, and terminology context
4. `Orchestrator` Organize segments into multiple bundles based on configuration, controlling the size of each model call
5. `TranslatorAgent` Translate each bundle
6. `ReviewerAgent` conditionally reviews in `balanced` / `strict` mode
7. `MarkdownRenderer` maps the translation results back to the AST and renders them as Markdown
8. `MarkdownValidator` validates the front matter and overall structure
9. If validation fails, `FormatGuardAgent` will attempt to fix formatting issues when necessary
10. Finally outputs the translated Markdown and optional report files

The goal of this mechanism is to preserve the original Markdown formatting as much as possible, while ensuring the translation results have sufficient contextual consistency and maintainability. 🛡️

## 🗂️ Project Structure

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

Other important files in the root directory:

- `config.yaml`: Example configuration
- `requirements.txt`: Runtime dependencies
- `doc/`: Multilingual README and design documents

## 🧪 Development and Testing

Install dependencies:

```bash
pip install -r requirements.txt
```

If you plan to package the exe yourself, you will also need:

```bash
pip install -r src/buildtool/requirements-build.txt
```

## Star History

<a href="https://star-history.com/#CrazyMayfly/Free-Markdown-Translator&Date">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=CrazyMayfly/Free-Markdown-Translator&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=CrazyMayfly/Free-Markdown-Translator&type=Date" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=CrazyMayfly/Free-Markdown-Translator&type=Date" />
 </picture>
</a>
