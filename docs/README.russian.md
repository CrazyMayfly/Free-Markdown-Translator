![Бесплатный переводчик Markdown](https://socialify.git.ci/CrazyMayfly/Free-Markdown-Translator/image?custom_description=Free+Markdown+Translator%E6%98%AF%E4%B8%80%E6%AC%BE%E5%9F%BA%E4%BA%8E+AI+Agent+%E6%B5%81%E6%B0%B4%E7%BA%BF%E7%9A%84+Markdown+%E6%96%87%E6%A1%A3%E7%BF%BB%E8%AF%91%E5%99%A8&description=1&font=Bitter&forks=1&language=1&name=1&owner=1&pattern=Solid&stargazers=1&theme=Auto)

# Бесплатный переводчик Markdown

Бесплатный переводчик Markdown — это инструмент перевода документов Markdown на основе конвейера AI Agent, который может переводить документы Markdown на любой язык, фокусируясь на максимальном сохранении исходной структуры Markdown при поддержании семантической связности. Он подходит для сценариев использования таких как сайты документации, локальные базы знаний, README, многоязычная техническая документация и т.д. ✨

## 🚀 Основные функции и возможности

- 🧠 Использование управляемого AI процесса перевода и проверки синтаксического дерева AST обеспечивает стабильность формата и более согласованный контекст
- ✂️ Можно настраивать языковой стиль, входное соответствие, формат вывода, поддерживаются различные режимы перевода (быстрый, сбалансированный, строгий) для адаптации к различным потребностям
- 🤖 Встроенные `TranslatorAgent`, `ReviewerAgent`, `FormatGuardAgent`, отвечающие соответственно за перевод, вычитку и исправление формата (включаются в зависимости от режима перевода)
- 🧱 Поддержка защиты структур: фронтматтер, уровни заголовков, списки, таблицы, блоки кода, ссылки и т.д.
- ✅ Предоставляет проверку структуры и отчеты о выводе, помогая обнаруживать дрейф формата и аномалии содержания
- 🔌 Совместимость с интерфейсами в стиле OpenAI, можно подключать OpenAI или другие совместимые сервисы
- ⚙️ Поддержка нескольких целевых языков, рекурсивный перевод каталогов, параллельная обработка, ограничения стиля текста и сохранение терминологии

## ⚡ Быстрый старт

### Способ 1: Запуск после клонирования репозитория

```bash
git clone https://github.com/CrazyMayfly/Free-Markdown-Translator.git
cd Free-Markdown-Translator
pip install -r requirements.txt
python src/cli/main.py --init-config
```

После инициализации файл конфигурации по умолчанию будет создан в:

```text
~/.mdtx/config.yaml
```

После настройки API Key можно начать перевод:

```bash
python src/cli/main.py README.md --to english,japanese
```

### Способ 2: Скачать exe и использовать напрямую

Если вы используете Windows, вы также можете скачать уже упакованный `mdtx.exe` и запустить его напрямую. При первом использовании рекомендуется сначала инициализировать конфигурацию:

```powershell
.\mdtx.exe --init-config
```

Затем отредактируйте:

```text
~/.mdtx/config.yaml
```

После завершения настройки можно выполнить:

```powershell
.\mdtx.exe README.md --to Chinese
```

### Примеры команд для распространенных сценариев

Перевод одного файла на китайский:

```bash
.\mdtx.exe README.md --to Chinese
```

Рекурсивный перевод всего каталога `doc` на английский и японский:

```bash
.\mdtx.exe doc --to english,japanese
```

Указать выходной каталог:

```bash
.\mdtx.exe README.md --to Chinese --output translated
```

Сопоставлять только Markdown-файлы с указанным форматом имени файла в каталоге (используя регулярные выражения):

```bash
.\mdtx.exe docs --to Chinese --match "name*.md"
```

Увеличить параллелизм для ускорения массового перевода:

```bash
.\mdtx.exe docs --to Chinese --threads 10
```

Включить более строгий процесс перевода и проверки: потребляет больше токенов и занимает больше времени, но обеспечивает лучшее качество перевода:

```bash
.\mdtx.exe docs --to Chinese --mode strict
```

Принудительно включить проверку и защиту формата:

```bash
.\mdtx.exe docs --to Chinese --review true --guard true
```

Переключить модель или стиль:

```bash
.\mdtx.exe README.md --to Chinese --model gpt-5-mini --tone technical
```

Выводить подробные логи для упрощения отладки:

```bash
.\mdtx.exe --verbose README.md --to Chinese
```

## ⚙️ Описание конфигурации

Проект будет искать конфигурационные файлы в следующем порядке приоритета:

1. `--config` указанный путь
2.  `config.yaml` в корневом каталоге репозитория
3. `src/config.yaml`
4. `~/.mdtx/config.yaml`

Пример типичной конфигурации:

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

### Пример конфигурации API Key

Рекомендуется использовать переменные окружения:

```powershell
$env:OPENAI_API_KEY="your-api-key"
.\mdtx.exe README.md --to Chinese
```

Также можно указать в файле конфигурации (не рекомендуется, существует риск безопасности):

```yaml
provider:
  api_key: xxxxx
```

Если вы используете совместимый интерфейс, это также можно изменить в `config.yaml`:

```yaml
provider:
  name: openai
  base_url: https://your-openai-compatible-endpoint/v1
  api_key_env: YOUR_API_KEY_ENV
  model: your-model-name
```

## 🔄 Процесс выполнения и механизм

Этот проект не «отправляет весь Markdown-документ модели для перевода за один раз», а представляет собой более надежный конвейер:

1. `MarkdownParser` Сначала исходный документ разбирается в AST, распознается структура Markdown
2. `SegmentExtractor` Из AST извлекаются переводимые фрагменты, защищаются плейсхолдеры, управляющий синтаксис и другой чувствительный контент
3. `DocumentContextBuilder` Генерируется сводка документа, ограничения стиля, контекст терминологии
4. `Orchestrator` Сегменты организуются в несколько пакетов (bundles) согласно конфигурации, контролируется размер каждого вызова модели
5. `TranslatorAgent` Переводится каждый пакет (bundle)
6. `ReviewerAgent` выполняет условную проверку в режиме `balanced` / `strict`
7. `MarkdownRenderer` сопоставляет результаты перевода обратно с AST и рендерит их в Markdown
8. `MarkdownValidator` валидирует front matter и общую структуру
9. Если валидация не удалась, `FormatGuardAgent` при необходимости попытается исправить проблемы форматирования
10. В итоге генерирует переведенный Markdown и опциональные файлы отчётов

Цель этого механизма: максимально сохранить исходный вид Markdown, обеспечив при этом достаточную контекстуальную согласованность и поддерживаемость результатов перевода. 🛡️

## 🗂️ Структура проекта

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

Другие важные файлы в корневой директории:

- `config.yaml`: пример конфигурации
- `requirements.txt`: зависимости для запуска
- `doc/`: многоязычные README и документы по дизайну

## 🧪 Разработка и тестирование

Установка зависимостей:

```bash
pip install -r requirements.txt
```

Если вы планируете самостоятельно упаковать exe, также потребуется:

```bash
pip install -r src/buildtool/requirements-build.txt
```

## История звёзд

<a href="https://star-history.com/#CrazyMayfly/Free-Markdown-Translator&Date">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=CrazyMayfly/Free-Markdown-Translator&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=CrazyMayfly/Free-Markdown-Translator&type=Date" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=CrazyMayfly/Free-Markdown-Translator&type=Date" />
 </picture>
</a>
