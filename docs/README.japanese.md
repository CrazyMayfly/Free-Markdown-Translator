![Free-Markdown-Translator](https://socialify.git.ci/CrazyMayfly/Free-Markdown-Translator/image?custom_description=Free+Markdown+Translator%E6%98%AF%E4%B8%80%E6%AC%BE%E5%9F%BA%E4%BA%8E+AI+Agent+%E6%B5%81%E6%B0%B4%E7%BA%BF%E7%9A%84+Markdown+%E6%96%87%E6%A1%A3%E7%BF%BB%E8%AF%91%E5%99%A8&description=1&font=Bitter&forks=1&language=1&name=1&owner=1&pattern=Solid&stargazers=1&theme=Auto)

# 無料 Markdown 翻訳ツール

Free Markdown Translator は、AI エージェントパイプラインに基づく Markdown ドキュメント翻訳ツールです。Markdown ドキュメントを任意の言語に翻訳可能で、翻訳過程中に元の Markdown 構造を可能な限り保持しつつ、意味の连贯性も維持することに注力しています。ドキュメントサイト、ローカルナレッジベース、README、多言語技術ドキュメントなどのシーンに適しています。 ✨

## 🚀 主な機能と特徴

- 🧠 AI 駆動の翻訳フローおよび AST 構文木検証を使用し、形式の安定性とより一貫した文脈の整合性を維持できます
- ✂️ 言語スタイル、入力マッチング、出力形式をカスタマイズ可能で、異なる翻訳モード（高速、バランス、厳格）をサポートし、さまざまなニーズに対応します
- 🤖 `TranslatorAgent`、`ReviewerAgent`、`FormatGuardAgent` を内蔵しており、それぞれ翻訳、校正、形式修復を担当します（翻訳モードに応じて有効化）
- 🧱 front matter、見出しレベル、リスト、テーブル、コードブロック、リンクなどの構造保護をサポートします
- ✅ 構造検証と出力レポートを提供し、形式のドリフトや内容の異常を発見するのに役立ちます
- 🔌 OpenAI スタイルのインターフェースと互換性があり、OpenAI または他の互換サービスに接続できます
- ⚙️ 複数の目標言語、ディレクトリ再帰翻訳、並列処理、文体制約、用語保持をサポートします

## ⚡ クイックスタート

### 方法 1：リポジトリをクローンして起動

```bash
git clone https://github.com/CrazyMayfly/Free-Markdown-Translator.git
cd Free-Markdown-Translator
pip install -r requirements.txt
python src/cli/main.py --init-config
```

初期化後、デフォルトの設定ファイルは以下に生成されます：

```text
~/.mdtx/config.yaml
```

API Key を設定した後、翻訳を開始できます：

```bash
python src/cli/main.py README.md --to english,japanese
```

### 方法 2：exe をダウンロードして直接使用

Windows を使用している場合は、パッケージ化された `mdtx.exe` をダウンロードして直接実行することもできます。初回使用時は、まず設定を初期化することをお勧めします：

```powershell
.\mdtx.exe --init-config
```

その後、編集します：

```text
~/.mdtx/config.yaml
```

設定完了後、実行できます：

```powershell
.\mdtx.exe README.md --to Chinese
```

### 一般的なユースケースのコマンド例

単一ファイルを中国語に翻訳：

```bash
.\mdtx.exe README.md --to Chinese
```

`doc` ディレクトリ全体を英語と日本語に再帰的に翻訳：

```bash
.\mdtx.exe doc --to english,japanese
```

出力ディレクトリの指定：

```bash
.\mdtx.exe README.md --to Chinese --output translated
```

ディレクトリ内の指定されたファイル名形式の Markdown ファイルのみをマッチします（正規表現を使用）：

```bash
.\mdtx.exe docs --to Chinese --match "name*.md"
```

並列度を上げて、大量翻訳を高速化します：

```bash
.\mdtx.exe docs --to Chinese --threads 10
```

より厳格な翻訳および検証プロセスを有効にします。より多くのトークンを消費し、時間がかかりますが、より良い翻訳結果が得られます：

```bash
.\mdtx.exe docs --to Chinese --mode quality
```

校閲とフォーマット保護を強制的に有効にします：

```bash
.\mdtx.exe docs --to Chinese --review true --guard true
```

モデルまたは文体を切り替えます：

```bash
.\mdtx.exe README.md --to Chinese --model gpt-5-mini --tone technical
```

詳細ログを出力し、トラブルシューティングを容易にします：

```bash
.\mdtx.exe --verbose README.md --to Chinese
```

## ⚙️ 設定説明

プロジェクトは以下の優先順位で設定ファイルを検索します：

1. `--config` で指定されたパス
2. リポジトリのルートディレクトリ下の `config.yaml`
3. `src/config.yaml`
4. `~/.mdtx/config.yaml`

典型的な設定は以下の通りです：

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
  # 强制开启审校 Agent。关闭时，balanced 只审可疑包，quality 全量审校。
  enable_review: false
  # 强制开启格式修复 Agent。关闭时，balanced/quality 遇到校验失败仍可能触发修复。
  enable_format_guard: false
  # 输出校验失败时是否直接报错。
  fail_on_validation_error: true

# 分段策略。先按 Markdown 结构（标题/列表/表格/引用）打包，超长块再按行拆分。
segmentation:
  max_bundle_tokens: 4000
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

### API Key 設定例

環境変数の使用を推奨します：

```powershell
$env:OPENAI_API_KEY="your-api-key"
.\mdtx.exe README.md --to Chinese
```

設定ファイルに記述することも可能です（非推奨、セキュリティリスクあり）：

```yaml
provider:
  api_key: xxxxx
```

互換インターフェースを使用する場合、`config.yaml` で変更することもできます：

```yaml
provider:
  name: openai
  base_url: https://your-openai-compatible-endpoint/v1
  api_key_env: YOUR_API_KEY_ENV
  model: your-model-name
```

## 🔄 実行フローと仕組み

このプロジェクトは「Markdown 文書全体を一度にモデルへ送信して翻訳する」ものではなく、より堅牢なパイプラインです：

1. `MarkdownParser` 最初にソースドキュメントを AST に解析し、Markdown 構造を識別します
2. `SegmentExtractor` AST から翻訳可能なセグメントを抽出し、プレースホルダー、制御構文などのセンシティブな内容を保護します
3. `DocumentContextBuilder` ドキュメントの要約、スタイル制約、用語コンテキストを生成します
4. `Orchestrator` 設定に基づきセグメントを複数のバンドルにグループ化し、モデル呼び出しごとのサイズを制御します
5. `TranslatorAgent` 各バンドルを翻訳します
6. `ReviewerAgent` は `balanced` / `quality` モードで条件に基づき校閲します
7. `MarkdownRenderer` は翻訳結果を AST に再マップし、Markdown としてレンダリングします
8. `MarkdownValidator` は front matter と全体の構造を検証します
9. 検証に失敗した場合、`FormatGuardAgent` は必要に応じて書式問題の修復を試みます
10. 最終的に翻訳された Markdown とオプションのレポートファイルを出力します

このメカニズムの目標は、Markdown の元の形式をできるだけ保持しつつ、翻訳結果に十分な文脈の一貫性と保守性を持たせることです。 🛡️

## 🗂️ プロジェクト構造

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

ルートディレクトリにあるその他の重要なファイル：

- `config.yaml`：設定例
- `requirements.txt`：ランタイム依存関係
- `doc/`：多言語 README と設計ドキュメント

## 🧪 開発とテスト

依存関係のインストール：

```bash
pip install -r requirements.txt
```

自分で exe をパッケージ化する場合は、さらに以下が必要です：

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
