![Free-Markdown-Translator](https://socialify.git.ci/CrazyMayfly/Free-Markdown-Translator/image?custom_description=Free+Markdown+Translator%E6%98%AF%E4%B8%80%E6%AC%BE%E5%9F%BA%E4%BA%8E+AI+Agent+%E6%B5%81%E6%B0%B4%E7%BA%BF%E7%9A%84+Markdown+%E6%96%87%E6%A1%A3%E7%BF%BB%E8%AF%91%E5%99%A8&description=1&font=Bitter&forks=1&language=1&name=1&owner=1&pattern=Solid&stargazers=1&theme=Auto)

# 무료 마크다운 번역기

무료 마크다운 번역기는 AI 에이전트 파이프라인 기반의 마크다운 문서 번역 도구로, 마크다운 문서를 모든 언어로 번역할 수 있으며, 번역 과정에서 원래 마크다운 구조를 최대한 유지하면서 의미적 일관성을 유지하는 데 중점을 둡니다. 문서 사이트, 로컬 지식 베이스, README, 다국어 기술 문서 등의 시나리오에 적합합니다. ✨

## 🚀 주요 기능 및 특성

- 🧠 AI 기반 번역 프로세스 및 AST 구문 트리 검증을 사용하여 형식 안정성과 더 일관된 컨텍스트 일관성을 유지할 수 있습니다
- ✂️ 언어 스타일, 입력 매칭, 출력 형식을 사용자 정의할 수 있으며, 다양한 요구 사항에 맞게 다양한 번역 모드 (빠름, 균형, 엄격) 를 지원합니다
- 🤖 `TranslatorAgent`, `ReviewerAgent`, `FormatGuardAgent` 를 내장하여 각각 번역, 검수 및 형식 수정을 담당합니다 (번역 모드에 따라 활성화)
- 🧱 front matter, 제목 수준, 목록, 표, 코드 블록, 링크 등의 구조 보호를 지원합니다
- ✅ 구조 검증 및 출력 보고서를 제공하여 형식 드리프트 및 콘텐츠 이상을 발견하는 데 도움을 줍니다
- 🔌 OpenAI 스타일 인터페이스와 호환되며, OpenAI 또는 기타 호환 서비스에 연결할 수 있습니다
- ⚙️ 다중 대상 언어, 디렉토리 재귀 번역, 병렬 처리, 문체 제약 및 용어 보존을 지원합니다

## ⚡ 빠른 시작

### 방법 1: 저장소 Clone 후 시작

```bash
git clone https://github.com/CrazyMayfly/Free-Markdown-Translator.git
cd Free-Markdown-Translator
pip install -r requirements.txt
python src/cli/main.py --init-config
```

초기화 후 기본 설정 파일이 다음 위치에 생성됩니다:

```text
~/.mdtx/config.yaml
```

API Key 를 설정한 후 번역을 시작할 수 있습니다:

```bash
python src/cli/main.py README.md --to english,japanese
```

### 방법 2: exe 다운로드 후 바로 사용

Windows 를 사용하는 경우, 이미 패키징된 `mdtx.exe` 를 다운로드하여 바로 실행할 수도 있습니다. 처음 사용할 때는 설정을 먼저 초기화하는 것을 권장합니다:

```powershell
.\mdtx.exe --init-config
```

그런 다음 편집:

```text
~/.mdtx/config.yaml
```

설정 완료 후 다음을 실행합니다:

```powershell
.\mdtx.exe README.md --to Chinese
```

### 자주 사용하는 시나리오 명령어 예시

단일 파일을 중국어로 번역:

```bash
.\mdtx.exe README.md --to Chinese
```

전체 `doc` 디렉토리를 영어와 일본어로 재귀적으로 번역:

```bash
.\mdtx.exe doc --to english,japanese
```

출력 디렉토리 지정:

```bash
.\mdtx.exe README.md --to Chinese --output translated
```

디렉토리 내 지정된 파일명 패턴의 Markdown 파일만 매칭합니다 (정규식 사용):

```bash
.\mdtx.exe docs --to Chinese --match "name*.md"
```

병렬성을 높여 대량 번역 속도를 향상시킵니다:

```bash
.\mdtx.exe docs --to Chinese --threads 10
```

더 엄격한 번역 및 검증 프로세스를 활성화합니다. 더 많은 토큰을 소비하고 시간이 더 소요되지만 더 나은 번역 결과를 얻습니다:

```bash
.\mdtx.exe docs --to Chinese --mode strict
```

검수 및 형식 보호를 강제로 활성화합니다:

```bash
.\mdtx.exe docs --to Chinese --review true --guard true
```

모델 또는 스타일을 전환합니다:

```bash
.\mdtx.exe README.md --to Chinese --model gpt-5-mini --tone technical
```

상세 로그를 출력하여 디버깅을 용이하게 합니다:

```bash
.\mdtx.exe --verbose README.md --to Chinese
```

## ⚙️ 구성 설명

프로젝트는 다음 우선순위로 구성 파일을 찾습니다:

1. `--config` 로 지정된 경로
2.  저장소 루트 디렉터리 내 `config.yaml`
3. `src/config.yaml`
4. `~/.mdtx/config.yaml`

일반적인 구성은 다음과 같습니다:

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

### API Key 구성 예시

환경 변수 사용을 권장합니다:

```powershell
$env:OPENAI_API_KEY="your-api-key"
.\mdtx.exe README.md --to Chinese
```

구성 파일에 작성할 수도 있습니다 (권장하지 않음, 보안 위험 있음):

```yaml
provider:
  api_key: xxxxx
```

호환 인터페이스를 사용하는 경우 `config.yaml` 에서 수정할 수도 있습니다:

```yaml
provider:
  name: openai
  base_url: https://your-openai-compatible-endpoint/v1
  api_key_env: YOUR_API_KEY_ENV
  model: your-model-name
```

## 🔄 실행 흐름 및 메커니즘

이 프로젝트는 "전체 Markdown 문서를 한 번에 모델에 전달하여 번역하는" 것이 아니라, 더 안정적인 파이프라인을 사용합니다:

1. `MarkdownParser` 소스 문서를 AST 로 파싱하여 Markdown 구조 식별
2. `SegmentExtractor` AST 에서 번역 가능한 세그먼트를 추출하고 플레이스홀더, 제어 구문 등 민감한 내용 보호
3. `DocumentContextBuilder` 문서 요약, 스타일 제약, 용어 컨텍스트 생성
4. `Orchestrator` 설정에 따라 segment 를 여러 bundle 로 구성하여 각 모델 호출의 크기 제어
5. `TranslatorAgent` 각 bundle 에 대해 번역 수행
6. `ReviewerAgent` 는 `balanced` / `strict` 모드에서 조건부 검토를 수행합니다
7. `MarkdownRenderer` 는 번역 결과를 AST 로 다시 매핑하고 Markdown 으로 렌더링합니다
8. `MarkdownValidator` 는 front matter 와 전체 구조를 검증합니다
9. 검증에 실패할 경우 `FormatGuardAgent` 는 필요시 형식 문제를 수정하려고 시도합니다
10. 최종적으로 번역된 Markdown 과 선택적 보고 파일을 출력합니다

이 메커니즘의 목표는 Markdown 의 원본 형태를 최대한 유지하면서도 번역 결과가 충분한 문맥 일관성과 유지 보수성을 갖도록 하는 것입니다. 🛡️

## 🗂️ 프로젝트 구조

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

루트 디렉토리의 기타 중요한 파일:

- `config.yaml`: 예제 구성
- `requirements.txt`: 실행 의존성
- `doc/`: 다국어 README 및 설계 문서

## 🧪 개발 및 테스트

의존성 설치:

```bash
pip install -r requirements.txt
```

직접 exe 를 패키징하려면 다음도 필요합니다:

```bash
pip install -r src/buildtool/requirements-build.txt
```

## 스타 히스토리

<a href="https://star-history.com/#CrazyMayfly/Free-Markdown-Translator&Date">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=CrazyMayfly/Free-Markdown-Translator&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=CrazyMayfly/Free-Markdown-Translator&type=Date" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=CrazyMayfly/Free-Markdown-Translator&type=Date" />
 </picture>
</a>
