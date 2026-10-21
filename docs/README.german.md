![Kostenloser Markdown-Übersetzer](https://socialify.git.ci/CrazyMayfly/Free-Markdown-Translator/image?custom_description=Free+Markdown+Translator%E6%98%AF%E4%B8%80%E6%AC%BE%E5%9F%BA%E4%BA%8E+AI+Agent+%E6%B5%81%E6%B0%B4%E7%BA%BF%E7%9A%84+Markdown+%E6%96%87%E6%A1%A3%E7%BF%BB%E8%AF%91%E5%99%A8&description=1&font=Bitter&forks=1&language=1&name=1&owner=1&pattern=Solid&stargazers=1&theme=Auto)

# Kostenloser Markdown-Übersetzer

Kostenloser Markdown-Übersetzer ist ein auf einer KI-Agenten-Pipeline basierendes Werkzeug zur Übersetzung von Markdown-Dokumenten, das Markdown-Dokumente in beliebige Sprachen übersetzen kann. Der Fokus liegt darauf, die ursprüngliche Markdown-Struktur während des Übersetzungsprozesses bestmöglich zu bewahren und gleichzeitig die semantische Kohärenz zu erhalten. Es eignet sich für Anwendungsfälle wie Dokumentationsseiten, lokale Wissensdatenbanken, READMEs und mehrsprachige technische Dokumentation. ✨

## 🚀 Hauptfunktionen und Merkmale

- 🧠 Nutzt einen KI-gesteuerten Übersetzungsprozess sowie AST-Syntaxbaum-Validierung, um die Formatstabilität und eine konsistentere Kontextkohärenz zu gewährleisten
- ✂️ Ermöglicht benutzerdefinierte Sprachstile, Input-Matching, Output-Formatierung und unterstützt verschiedene Übersetzungsmodi (Schnell, Ausgewogen, Streng), um unterschiedliche Anforderungen zu erfüllen
- 🤖 Integriert `TranslatorAgent`, `ReviewerAgent`, `FormatGuardAgent`, die jeweils für Übersetzung, Prüfung und Formatbereinigung verantwortlich sind (aktiviert je nach Übersetzungsmodus)
- 🧱 Unterstützt den Schutz von Strukturen wie Front Matter, Überschriftenebenen, Listen, Tabellen, Code-Blöcken, Links usw.
- ✅ Bietet Strukturvalidierung und Ausgabebericht, um Formatdrift und Inhaltsanomalien zu erkennen
- 🔌 Kompatibel mit OpenAI-konformen Schnittstellen, Anbindung an OpenAI oder andere kompatible Dienste möglich
- ⚙️ Unterstützt mehrere Zielsprachen, rekursive Verzeichnisübersetzung, Parallelverarbeitung, Stilvorgaben und Terminologie-Erhalt

## ⚡ Schnellstart

### Methode 1: Repository klonen und starten

```bash
git clone https://github.com/CrazyMayfly/Free-Markdown-Translator.git
cd Free-Markdown-Translator
pip install -r requirements.txt
python src/cli/main.py --init-config
```

Nach der Initialisierung wird die Standardkonfigurationsdatei erstellt in:

```text
~/.mdtx/config.yaml
```

Sobald der API-Schlüssel konfiguriert ist, können Sie mit der Übersetzung beginnen:

```bash
python src/cli/main.py README.md --to english,japanese
```

### Methode 2: Exe-Datei herunterladen und direkt verwenden

Falls Sie Windows verwenden, können Sie auch die vorgepackte `mdtx.exe` herunterladen und direkt ausführen. Es wird empfohlen, beim ersten Mal zuerst die Konfiguration zu initialisieren:

```powershell
.\mdtx.exe --init-config
```

Bearbeiten Sie anschließend:

```text
~/.mdtx/config.yaml
```

Nachdem die Konfiguration abgeschlossen ist, führen Sie aus:

```powershell
.\mdtx.exe README.md --to Chinese
```

### Beispiele für Befehle in typischen Anwendungsfällen

Einzelne Datei ins Chinesische übersetzen:

```bash
.\mdtx.exe README.md --to Chinese
```

Das gesamte `doc`-Verzeichnis rekursiv ins Englische und Japanische übersetzen:

```bash
.\mdtx.exe doc --to english,japanese
```

Ausgabeverzeichnis angeben:

```bash
.\mdtx.exe README.md --to Chinese --output translated
```

Nur Markdown-Dateien mit angegebenen Dateinamenformaten im Verzeichnis matchen (Regex-basiert):

```bash
.\mdtx.exe docs --to Chinese --match "name*.md"
```

Parallelität erhöhen, um Massentranslationen zu beschleunigen:

```bash
.\mdtx.exe docs --to Chinese --threads 10
```

Strengere Übersetzungs- und Validierungsprozesse aktivieren: Mehr Tokenverbrauch und Laufzeit, dafür bessere Ergebnisse:

```bash
.\mdtx.exe docs --to Chinese --mode strict
```

Überprüfung und Formatschutz erzwingen:

```bash
.\mdtx.exe docs --to Chinese --review true --guard true
```

Modell oder Stil wechseln:

```bash
.\mdtx.exe README.md --to Chinese --model gpt-5-mini --tone technical
```

Detaillierte Logs ausgeben, zur Fehlerdiagnose:

```bash
.\mdtx.exe --verbose README.md --to Chinese
```

## ⚙️ Konfigurationshinweise

Das Projekt sucht Konfigurationsdateien in folgender Prioritätsreihenfolge:

1. `--config` angegebener Pfad
2.  im Repository-Wurzelverzeichnis
3. `src/config.yaml`
4. `~/.mdtx/config.yaml`

Eine typische Konfiguration sieht wie folgt aus:

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

# 分段策略。先按 Markdown 结构（标题/列表/表格/引用）打包，超长块再按行拆分。
segmentation:
  max_bundle_tokens: 3000
  min_bundle_tokens: 800

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

### Beispiel für die API-Key-Konfiguration

Die Verwendung von Umgebungsvariablen wird empfohlen:

```powershell
$env:OPENAI_API_KEY="your-api-key"
.\mdtx.exe README.md --to Chinese
```

Alternativ kann es in der Konfigurationsdatei gespeichert werden (nicht empfohlen, Sicherheitsrisiko):

```yaml
provider:
  api_key: xxxxx
```

Falls Sie eine kompatible Schnittstelle verwenden, können Sie dies auch in `config.yaml` anpassen:

```yaml
provider:
  name: openai
  base_url: https://your-openai-compatible-endpoint/v1
  api_key_env: YOUR_API_KEY_ENV
  model: your-model-name
```

## 🔄 Ausführungsprozess und Mechanismen

Dieses Projekt ist kein Ansatz, bei dem das gesamte Markdown-Dokument auf einmal an das Modell zur Übersetzung übergeben wird, sondern ein sichererer Pipeline-Prozess:

1. `MarkdownParser` Parsen Sie zunächst das Quelldokument in ein AST, um die Markdown-Struktur zu erkennen.
2. `SegmentExtractor` Extrahieren Sie übersetzbare Abschnitte aus dem AST und schützen Sie Platzhalter, Kontrollsyntax und andere sensible Inhalte.
3. `DocumentContextBuilder` Generieren Sie Dokumentzusammenfassungen, Stilbeschränkungen und Terminologiekontext.
4. `Orchestrator` Organisieren Sie Segmente gemäß der Konfiguration in mehrere Bundles und steuern Sie die Größe jedes Modellaufrufs.
5. `TranslatorAgent` Übersetzen Sie jedes Bundle.
6. `ReviewerAgent` führt eine bedingte Prüfung im `balanced` / `strict`-Modus durch
7. `MarkdownRenderer` ordnet die Übersetzungsergebnisse wieder dem AST zu und rendert sie als Markdown
8. `MarkdownValidator` validiert Front Matter und die Gesamtstruktur
9. Falls die Validierung fehlschlägt, versucht `FormatGuardAgent`, Formatierungsprobleme bei Bedarf zu korrigieren
10. Abschließend wird das übersetzte Markdown sowie optionale Report-Dateien ausgegeben

{{MD_0}}Ziel dieses Mechanismus ist es, das Markdown-Originalformat so weit wie möglich zu bewahren und gleichzeitig für hinreichende Kontextkohärenz und Wartbarkeit der Übersetzungsergebnisse zu sorgen. 🛡️

## 🗂️ Projektstruktur

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

{{MD_0}}Weitere wichtige Dateien im Wurzelverzeichnis:

- `config.yaml`: Beispielkonfiguration
- `requirements.txt`: Laufzeitabhängigkeiten
- `doc/`: Mehrsprachiges README und Design-Dokumentation

## 🧪 Entwicklung und Tests

Abhängigkeiten installieren:

```bash
pip install -r requirements.txt
```

Wenn du eine EXE selbst verpacken möchtest, benötigst du zudem:

```bash
pip install -r src/buildtool/requirements-build.txt
```

## Stern-Historie

<a href="https://star-history.com/#CrazyMayfly/Free-Markdown-Translator&Date">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=CrazyMayfly/Free-Markdown-Translator&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=CrazyMayfly/Free-Markdown-Translator&type=Date" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=CrazyMayfly/Free-Markdown-Translator&type=Date" />
 </picture>
</a>
