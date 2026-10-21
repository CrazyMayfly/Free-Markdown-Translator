![Tradutor-Markdown-Gratuito](https://socialify.git.ci/CrazyMayfly/Free-Markdown-Translator/image?custom_description=Free+Markdown+Translator%E6%98%AF%E4%B8%80%E6%AC%BE%E5%9F%BA%E4%BA%8E+AI+Agent+%E6%B5%81%E6%B0%B4%E7%BA%BF%E7%9A%84+Markdown+%E6%96%87%E6%A1%A3%E7%BF%BB%E8%AF%91%E5%99%A8&description=1&font=Bitter&forks=1&language=1&name=1&owner=1&pattern=Solid&stargazers=1&theme=Auto)

# Free Markdown Translator

O Free Markdown Translator é uma ferramenta de tradução de documentos Markdown baseada em um pipeline de AI Agent. Ele pode traduzir documentos Markdown para qualquer idioma, focando em preservar a estrutura original do Markdown durante o processo de tradução, mantendo simultaneamente a coerência semântica. É adequado para cenários como sites de documentação, bases de conhecimento locais, READMEs, documentos técnicos multilíngues, etc. ✨

## 🚀 Principais Funcionalidades e Características

- 🧠 Utiliza um fluxo de tradução impulsionado por IA e validação de árvore sintática AST para manter a estabilidade do formato e uma consistência de contexto mais coerente
- ✂️ Permite personalizar o estilo de linguagem, correspondência de entrada e formato de saída, suportando diferentes modos de tradução (Rápido, Equilibrado, Estrito) para atender a diferentes necessidades
- 🤖 Incorpora `TranslatorAgent`, `ReviewerAgent`, `FormatGuardAgent`, responsáveis respectivamente por tradução, revisão e correção de formato (ativados conforme o modo de tradução)
- 🧱 Suporta proteção de estruturas como front matter, níveis de cabeçalho, listas, tabelas, blocos de código, links, etc.
- ✅ Fornece validação de estrutura e relatórios de saída para ajudar a detectar desvios de formato e anomalias de conteúdo
- 🔌 Compatível com interfaces no estilo OpenAI, podendo conectar-se ao OpenAI ou outros serviços compatíveis
- ⚙️ Suporta múltiplos idiomas de destino, tradução recursiva de diretórios, processamento paralelo, restrições de estilo de escrita e preservação de termos

## ⚡ Início Rápido

### Método 1: Iniciar após clonar o repositório

```bash
git clone https://github.com/CrazyMayfly/Free-Markdown-Translator.git
cd Free-Markdown-Translator
pip install -r requirements.txt
python src/cli/main.py --init-config
```

Após a inicialização, o arquivo de configuração padrão será gerado em:

```text
~/.mdtx/config.yaml
```

Após configurar a API Key, você pode começar a traduzir:

```bash
python src/cli/main.py README.md --to english,japanese
```

### Método 2: Baixar o exe e usar diretamente

Se você estiver usando Windows, também pode baixar o `mdtx.exe` já empacotado e executá-lo diretamente. Para a primeira utilização, recomenda-se inicializar a configuração primeiro:

```powershell
.\mdtx.exe --init-config
```

Em seguida, edite:

```text
~/.mdtx/config.yaml
```

Após concluir a configuração, você pode executar:

```powershell
.\mdtx.exe README.md --to Chinese
```

### Exemplos de comandos para cenários comuns

Traduzir arquivo único para chinês:

```bash
.\mdtx.exe README.md --to Chinese
```

Traduzir recursivamente todo o diretório `doc` para inglês e japonês:

```bash
.\mdtx.exe doc --to english,japanese
```

Especificar diretório de saída:

```bash
.\mdtx.exe README.md --to Chinese --output translated
```

Apenas corresponder a arquivos Markdown com formatos de nome de arquivo especificados no diretório (usando correspondência regex):

```bash
.\mdtx.exe docs --to Chinese --match "name*.md"
```

Aumentar o paralelismo para acelerar traduções em grande lote:

```bash
.\mdtx.exe docs --to Chinese --threads 10
```

Ativar um processo de tradução e verificação mais rigoroso, consome mais tokens, leva mais tempo, mas obtém melhores resultados de tradução:

```bash
.\mdtx.exe docs --to Chinese --mode strict
```

Forçar a ativação de revisão e proteção de formato:

```bash
.\mdtx.exe docs --to Chinese --review true --guard true
```

Alternar modelo ou estilo de escrita:

```bash
.\mdtx.exe README.md --to Chinese --model gpt-5-mini --tone technical
```

Gerar logs detalhados para facilitar a depuração:

```bash
.\mdtx.exe --verbose README.md --to Chinese
```

## ⚙️ Instruções de Configuração

O projeto procurará arquivos de configuração na seguinte ordem de prioridade:

1. `--config` caminho especificado
2.  no diretório raiz do repositório
3. `src/config.yaml`
4. `~/.mdtx/config.yaml`

Uma configuração típica é a seguinte:

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

### Exemplo de Configuração da API Key

Recomenda-se o uso de variáveis de ambiente:

```powershell
$env:OPENAI_API_KEY="your-api-key"
.\mdtx.exe README.md --to Chinese
```

Também pode ser escrito no arquivo de configuração (não recomendado, há riscos de segurança):

```yaml
provider:
  api_key: xxxxx
```

Se você usar uma interface compatível, também pode modificar em `config.yaml`:

```yaml
provider:
  name: openai
  base_url: https://your-openai-compatible-endpoint/v1
  api_key_env: YOUR_API_KEY_ENV
  model: your-model-name
```

## 🔄 Fluxo de Execução e Mecanismo

Este projeto não é "jogar todo o Markdown para o modelo traduzir de uma vez", mas sim um pipeline mais confiável:

1. `MarkdownParser` Primeiro analisa o documento fonte em AST, identificando a estrutura Markdown
2. `SegmentExtractor` Extrai segmentos traduzíveis do AST e protege placeholders, sintaxe de controle e outros conteúdos sensíveis
3. `DocumentContextBuilder` Gera resumo do documento, restrições de estilo, contexto de terminologia
4. `Orchestrator` Organiza os segments em múltiplos bundles conforme a configuração, controlando o tamanho de cada chamada ao modelo
5. `TranslatorAgent` Traduz cada bundle
6. `ReviewerAgent` realiza revisão condicional no modo `balanced` / `strict`
7. `MarkdownRenderer` mapeia o resultado da tradução de volta para a AST e renderiza como Markdown
8. `MarkdownValidator` valida o front matter e a estrutura geral
9. Se a validação falhar, `FormatGuardAgent` tentará corrigir problemas de formatação, se necessário
10. Produz finalmente o Markdown traduzido e arquivos de relatório opcionais

O objetivo deste mecanismo é: preservar ao máximo a aparência original do Markdown, enquanto garante que o resultado da tradução tenha consistência de contexto e manutenibilidade suficientes. 🛡️

## 🗂️ Estrutura do Projeto

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

Outros arquivos importantes no diretório raiz:

- `config.yaml`: Configuração de exemplo
- `requirements.txt`: Dependências de execução
- `doc/`: README multilíngue e documentos de design

## 🧪 Desenvolvimento e Testes

Instalar dependências:

```bash
pip install -r requirements.txt
```

Se você pretende empacotar o exe por conta própria, também precisará:

```bash
pip install -r src/buildtool/requirements-build.txt
```

## Histórico de Stars

<a href="https://star-history.com/#CrazyMayfly/Free-Markdown-Translator&Date">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=CrazyMayfly/Free-Markdown-Translator&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=CrazyMayfly/Free-Markdown-Translator&type=Date" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=CrazyMayfly/Free-Markdown-Translator&type=Date" />
 </picture>
</a>
